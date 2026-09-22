from __future__ import annotations

import http.client
import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from experiment.config import ExperimentConfig
from experiment.runner import ExperimentListener, ExperimentRunner
from medsim.models import CaseStudy
from tests.conftest import ScriptedLLM, make_settings
from tests.experiment.helpers import CASES, FakeEnvironment, ScriptedStrategy
from webapp.server import App, Reply, RunManager, create_server

ROOT = Path(__file__).resolve().parents[2]


class Gate:
    """Holds every environment query until opened, so a run stays in progress."""

    def __init__(self) -> None:
        self.event = threading.Event()

    def environment(self, case: CaseStudy) -> FakeEnvironment:
        gate = self.event

        class Held(FakeEnvironment):
            def query(self, query: str) -> Any:
                gate.wait(10)
                return super().query(query)

        return Held(case)


def fake_runner_factory(gate: Gate | None = None) -> Any:
    def factory(config: ExperimentConfig, *, listener: ExperimentListener) -> ExperimentRunner:
        return ExperimentRunner(
            config,
            listener=listener,
            settings=make_settings(),
            llm=ScriptedLLM(),
            environment_factory=gate.environment if gate else FakeEnvironment,
            strategies={key: ScriptedStrategy() for key in config.strategy_keys},
        )

    return factory


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project folder with a config, a case file, and no .env (the key comes from the env)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    (tmp_path / "cases").mkdir()
    (tmp_path / "cases" / "cases.json").write_text(json.dumps(CASES), encoding="utf-8")
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "basic.json").write_text(json.dumps(config_data()), encoding="utf-8")
    return tmp_path


def config_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": "web",
        "cases_file": "cases/cases.json",
        "max_cases": 2,
        "strategies": ["basic"],
        "stopping": {"max_iterations": 2},
        "workers": 2,
        "output": "records/{name}.json",
    }
    return data | overrides


def call(app: App, method: str, target: str, body: Any = None) -> tuple[int, Any]:
    raw = json.dumps(body).encode() if body is not None else b""
    reply: Reply = app.handle(method, target, raw)
    content = reply.body.decode("utf-8")
    return reply.status, json.loads(content) if "json" in reply.content_type else content


def wait_for(app: App, state: str) -> dict[str, Any]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        _, status = call(app, "GET", "/api/runs/current")
        if status["state"] == state:
            return status  # type: ignore[no-any-return]
        time.sleep(0.02)
    raise AssertionError(f"run never reached {state}: {status}")


def test_page_and_options(project: Path) -> None:
    app = App(project)
    status, page = call(app, "GET", "/")
    assert status == 200 and "Information Gathering Strategy" in page
    assert call(app, "GET", "/static/app.js")[0] == 200
    assert call(app, "GET", "/static/../server.py")[0] == 404
    status, options = call(app, "GET", "/api/options")
    assert status == 200
    assert options["configs"] == ["basic.json"]
    assert options["case_files"] == ["cases/cases.json"]
    assert [s["name"] for s in options["strategies"]] == ["basic"]
    assert "openrouter_api_key" not in options["environment_settings"]
    assert options["environment_settings"]["max_documents"] == 8


def test_configs_are_read_and_saved_only_inside_configs(project: Path) -> None:
    app = App(project)
    status, config = call(app, "GET", "/api/configs/basic.json")
    assert status == 200 and config["name"] == "web"
    status, saved = call(app, "PUT", "/api/configs/mine.json", config_data(name="mine"))
    assert (status, saved) == (200, {"saved": "configs/mine.json"})
    stored = json.loads((project / "configs" / "mine.json").read_text())
    assert stored["strategies"] == [{"name": "basic", "label": None, "params": {}}]
    assert call(app, "PUT", "/api/configs/..%2Fescape.json", config_data())[0] == 400
    assert call(app, "PUT", "/api/configs/bad.json", {"name": "x"})[0] == 422
    assert not (project / "configs" / "bad.json").exists()


def test_validate_reports_the_plan_or_the_problem(project: Path) -> None:
    app = App(project)
    status, result = call(app, "POST", "/api/validate", config_data())
    assert status == 200 and result["ok"], result
    plan = result["plan"]
    assert (plan["cases"], plan["case_runs"], plan["max_iterations"]) == (2, 2, 4)
    assert plan["output"] == "records/web.json"
    _, bad = call(app, "POST", "/api/validate", config_data(case_ids=["NOPE"]))
    assert not bad["ok"] and "NOPE" in bad["error"]
    _, bad = call(
        app,
        "POST",
        "/api/validate",
        config_data(strategies=[{"name": "basic", "params": {"x": 1}}]),
    )
    assert not bad["ok"] and "Invalid params" in bad["error"]


def test_run_progress_and_record(project: Path) -> None:
    gate = Gate()
    app = App(project, RunManager(fake_runner_factory(gate)))
    assert call(app, "GET", "/api/runs/current")[1] == {"state": "idle"}

    status, started = call(app, "POST", "/api/runs", config_data())
    assert status == 202 and started["plan"]["case_runs"] == 2
    running = wait_for(app, "running")
    assert running["total"] == 2 and running["record"] == "records/web.json"
    assert call(app, "POST", "/api/runs", config_data())[0] == 409  # one at a time

    gate.event.set()
    done = wait_for(app, "completed")
    assert (done["finished"], done["iterations"], done["fraction"]) == (2, 4, 1.0)
    _, listing = call(app, "GET", "/api/records")
    assert [r["path"] for r in listing["records"]] == ["records/web.json"]
    status, record = call(app, "GET", "/api/record?path=records/web.json")
    assert status == 200 and record["status"] == "completed"
    assert [len(r["iterations"]) for r in record["case_runs"]] == [2, 2]


def test_cancel_a_run(project: Path) -> None:
    gate = Gate()
    app = App(project, RunManager(fake_runner_factory(gate)))
    call(app, "POST", "/api/runs", config_data(max_cases=None, workers=1))
    wait_for(app, "running")
    assert call(app, "POST", "/api/runs/current/cancel", {})[1] == {"cancelled": True}
    gate.event.set()
    done = wait_for(app, "cancelled")
    assert done["finished"] < 6


def test_a_config_problem_fails_the_run_visibly(project: Path) -> None:
    app = App(project, RunManager(fake_runner_factory()))
    status, reply = call(app, "POST", "/api/runs", config_data(cases_file="cases/missing.json"))
    assert status == 422 and "does not exist" in reply["error"]


def test_partial_records_and_paths_outside_the_project(project: Path, tmp_path: Path) -> None:
    app = App(project)
    records = project / "records"
    records.mkdir()
    header = {"type": "header", "format": "ics-experiment-record", "name": "p",
              "status": "running", "started_at": "2026-09-22T00:00:00+00:00",
              "output": "records/p.json", "config": config_data(),
              "environment_settings": {}, "strategies": {}, "case_ids": [],
              "case_runs_total": 1}  # fmt: skip
    (records / "p.partial.jsonl").write_text(json.dumps(header) + "\n{broken", encoding="utf-8")
    status, record = call(app, "GET", "/api/record?path=records/p.partial.jsonl")
    assert status == 200 and record["status"] == "running" and record["case_runs"] == []
    assert call(app, "GET", "/api/record?path=/etc/passwd")[0] == 403
    assert call(app, "GET", "/api/record?path=records/none.json")[0] == 404


def test_stored_environment_runs_are_listed_and_loaded() -> None:
    app = App(ROOT)
    _, listing = call(app, "GET", "/api/environment-runs")
    paths = {r["path"]: r for r in listing["runs"]}
    assert paths["environment/runs/live_runs_PMC3056427_01.json"]["questions"] == 2
    benchmark = "environment/results/retrieval_benchmark/runs/improved_1to4.jsonl"
    assert paths[benchmark]["kind"] == "retrieval_benchmark"

    live_path = "environment/runs/live_runs_PMC3056427_01.json"
    _, live = call(app, "GET", f"/api/environment-run?path={live_path}")
    (session,) = live["sessions"]
    assert session["case"]["diagnosis"] == "Tricuspid Valve Regurgitation"
    assert [q["response"]["answer_source"] for q in session["questions"]] == [
        "case_study", "literature"
    ]  # fmt: skip

    _, example = call(app, "GET", "/api/environment-run?path=environment/runs/example_runs.json")
    assert example["sessions"][0]["case"]["case_id"] == "test-urti-001"  # read from its case file

    _, bench = call(app, "GET", f"/api/environment-run?path={benchmark}")
    questions = [q for s in bench["sessions"] for q in s["questions"]]
    assert len(questions) == 50
    graded = [q for q in questions if q["grades"]]
    assert graded and all(
        set(g) >= {"relevance", "usefulness"} for q in graded for g in q["grades"].values()
    )
    assert any(q["truth"] and q["answer_verdict"] for q in questions)
    assert call(app, "GET", "/api/environment-run?path=pyproject.toml")[0] == 404


def test_http_server_checks_host_and_content_type(project: Path) -> None:
    server = create_server(App(project), port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:

        def request(method: str, path: str, host: str, body: str | None = None,
                    content_type: str | None = None) -> int:  # fmt: skip
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            headers = {"Host": host}
            if content_type:
                headers["Content-Type"] = content_type
            conn.request(method, path, body=body, headers=headers)
            status = conn.getresponse().status
            conn.close()
            return status

        assert request("GET", "/", f"127.0.0.1:{port}") == 200
        assert request("GET", "/", f"localhost:{port}") == 200
        assert request("GET", "/api/options", f"evil.example:{port}") == 403
        body, host = json.dumps(config_data()), f"localhost:{port}"
        assert request("POST", "/api/validate", host, body, "text/plain") == 415
        assert request("POST", "/api/validate", host, body, "application/json") == 200
    finally:
        server.shutdown()
        server.server_close()
