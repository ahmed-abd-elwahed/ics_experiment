from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from experiment.config import partial_path
from experiment.environment import MedsimEnvironmentFactory
from experiment.progress import ProgressTracker
from experiment.record import CaseRun, ExperimentRecord, environment_cost, load_record
from experiment.runner import ExperimentListener, ExperimentRunner
from medsim.environment import MedicalEnvironment
from medsim.models import CaseStudy
from strategies import BasicStrategy, build_strategy
from tests.conftest import ScriptedLLM, make_settings
from tests.environment.test_environment import resolver
from tests.experiment.helpers import (
    ConcurrencyTracker,
    FakeEnvironment,
    ManualClock,
    ScriptedStrategy,
    make_config,
    response,
    write_cases,
)


def runner_for(
    tmp_path: Path,
    *,
    strategies: dict[str, Any] | None = None,
    env_kwargs: dict[str, Any] | None = None,
    listener: ExperimentListener | None = None,
    clock: ManualClock | None = None,
    **config: Any,
) -> tuple[ExperimentRunner, dict[str, list[FakeEnvironment]]]:
    cfg = make_config(write_cases(tmp_path), **config)
    environments: dict[str, list[FakeEnvironment]] = {}

    def factory(case: CaseStudy) -> FakeEnvironment:
        env = FakeEnvironment(case, **(env_kwargs or {}))
        environments.setdefault(case.case_id, []).append(env)
        return env

    kwargs: dict[str, Any] = {"clock": clock} if clock is not None else {}
    runner = ExperimentRunner(
        cfg,
        listener=listener,
        settings=make_settings(),
        llm=ScriptedLLM(),
        environment_factory=factory,
        strategies=strategies or {s.key: ScriptedStrategy() for s in cfg.strategies},
        **kwargs,
    )
    return runner, environments


def test_each_case_runs_until_the_iteration_limit(tmp_path: Path) -> None:
    strategy = ScriptedStrategy()
    runner, environments = runner_for(tmp_path, strategies={"scripted": strategy}, max_cases=2)
    record = runner.run()

    assert record.status == "completed"
    assert [run.case_id for run in record.case_runs] == ["CASE1", "CASE2"]
    for run in record.case_runs:
        assert run.status == "completed"
        assert run.stop_reason == "max_iterations"
        assert [it.question for it in run.iterations] == [
            "Q question 1?", "Q question 2?", "Q question 3?"
        ]  # fmt: skip
        assert [it.answer for it in run.iterations] == [
            f"answer {n} for {run.case_id}" for n in (1, 2, 3)
        ]
        n = run.case_id[-1]
        assert run.case.narrative == f"Patient {n} presented with fever. Case {n}, second part."
        assert run.strategy_cost_usd == pytest.approx(0.0015)
        assert run.environment_cost_usd == pytest.approx(0.003)
    # every case got its own environment, and the strategy saw every earlier answer
    assert {k: len(v) for k, v in environments.items()} == {"CASE1": 1, "CASE2": 1}
    first = strategy.sessions[0]
    assert first.seen[2] == [
        ("Q question 1?", "answer 1 for CASE1"),
        ("Q question 2?", "answer 2 for CASE1"),
    ]
    assert record.summary["overall"]["iterations"] == 6
    assert record.summary["by_strategy"]["scripted"]["stop_reasons"] == {"max_iterations": 2}


def test_record_is_saved_and_the_partial_file_removed(tmp_path: Path) -> None:
    seen_partial: list[ExperimentRecord] = []

    class Peek(ExperimentListener):
        def case_finished(self, case_run: CaseRun) -> None:
            seen_partial.append(load_record(partial_path(runner.prepare().output)))

    runner, _ = runner_for(tmp_path, listener=Peek(), max_cases=2)
    record = runner.run()
    output = Path(record.output)

    assert output == tmp_path / "records" / "test.json"
    assert not partial_path(output).exists()
    assert load_record(output) == record
    # while running, each finished case run was already on disk
    assert [len(r.case_runs) for r in seen_partial] == [1, 2]
    assert all(r.status == "running" for r in seen_partial)
    assert record.environment_settings["default_model"] == make_settings().default_model
    assert "openrouter_api_key" not in record.environment_settings
    assert record.strategies["scripted"]["name"] == "scripted"
    assert "OPENROUTER" not in output.read_text(encoding="utf-8")


def test_time_limit_stops_a_case_run(tmp_path: Path) -> None:
    clock = ManualClock()
    runner, _ = runner_for(
        tmp_path,
        clock=clock,
        env_kwargs={"clock": clock, "seconds_per_query": 25.0},
        max_cases=1,
        stopping={"max_iterations": None, "max_seconds": 60},
    )
    run = runner.run().case_runs[0]
    # checked before each iteration: 0 s, 25 s, 50 s ask; at 75 s the limit has passed
    assert len(run.iterations) == 3
    assert run.stop_reason == "max_seconds"
    assert run.elapsed_s == 75.0


def test_whichever_limit_comes_first(tmp_path: Path) -> None:
    clock = ManualClock()
    runner, _ = runner_for(
        tmp_path,
        clock=clock,
        env_kwargs={"clock": clock, "seconds_per_query": 1.0},
        max_cases=1,
        stopping={"max_iterations": 2, "max_seconds": 60},
    )
    assert runner.run().case_runs[0].stop_reason == "max_iterations"


def test_strategy_can_stop_by_itself(tmp_path: Path) -> None:
    runner, _ = runner_for(
        tmp_path, strategies={"scripted": ScriptedStrategy(stop_after=1)}, max_cases=1
    )
    run = runner.run().case_runs[0]
    assert run.stop_reason == "strategy_done"
    assert len(run.iterations) == 1


def test_a_failed_case_run_is_recorded_and_the_experiment_continues(tmp_path: Path) -> None:
    runner, _ = runner_for(tmp_path, env_kwargs={"fail_on": 2}, max_cases=2)
    record = runner.run()
    assert record.status == "completed"
    for run in record.case_runs:
        assert run.status == "error"
        assert run.stop_reason == "error"
        assert "OpenRouter HTTP 502" in (run.error or "")
        assert [it.error is None for it in run.iterations] == [True, False]
        assert run.iterations[1].answer is None
    assert record.summary["overall"]["errors"] == 2


def test_case_runs_run_in_parallel_and_keep_config_order(tmp_path: Path) -> None:
    tracker = ConcurrencyTracker()
    config = make_config(
        write_cases(tmp_path),
        strategies=[{"name": "scripted", "label": "a"}, {"name": "scripted", "label": "b"}],
        workers=4,
        stopping={"max_iterations": 2},
    )
    runner = ExperimentRunner(
        config,
        settings=make_settings(),
        llm=ScriptedLLM(),
        environment_factory=lambda case: FakeEnvironment(case, sleep=0.02, tracker=tracker),
        strategies={"a": ScriptedStrategy(prefix="A"), "b": ScriptedStrategy(prefix="B")},
    )
    record = runner.run()

    assert tracker.peak > 1
    assert [(run.index, run.case_id, run.strategy) for run in record.case_runs] == [
        (i * 2 + j, f"CASE{i + 1}", label) for i in range(6) for j, label in enumerate("ab")
    ]
    assert all(run.iterations[0].question == f"{run.strategy.upper()} question 1?"
               for run in record.case_runs)  # fmt: skip
    assert set(record.summary["by_strategy"]) == {"a", "b"}


def test_cancel_stops_running_and_pending_case_runs(tmp_path: Path) -> None:
    class CancelInSecondCase(ExperimentListener):
        def case_started(self, index: int, case_id: str, strategy: str) -> None:
            if index == 1:
                runner.cancel()

    runner, _ = runner_for(tmp_path, listener=CancelInSecondCase())
    record = runner.run()
    assert record.status == "cancelled"
    assert [(run.case_id, run.status, len(run.iterations)) for run in record.case_runs] == [
        ("CASE1", "completed", 3),
        ("CASE2", "cancelled", 0),  # stopped before its first iteration; CASE3-6 never started
    ]
    assert record.case_runs[1].stop_reason == "cancelled"
    assert load_record(record.output).status == "cancelled"


def test_strategy_context_carries_the_limits(tmp_path: Path) -> None:
    strategy = ScriptedStrategy()
    runner, _ = runner_for(tmp_path, strategies={"scripted": strategy}, max_cases=1)
    runner.run()
    assert strategy.sessions[0].context.max_iterations == 3


def test_progress_tracker_follows_the_run(tmp_path: Path) -> None:
    tracker = ProgressTracker()
    runner, _ = runner_for(tmp_path, listener=tracker, max_cases=2)
    runner.run()
    snap = tracker.snapshot()
    assert snap["state"] == "completed"
    assert (snap["finished"], snap["total"], snap["iterations"]) == (2, 2, 6)
    assert snap["fraction"] == 1.0
    assert snap["cost_usd"] == pytest.approx(6 * 0.0015)
    assert [r["case_id"] for r in snap["recent"]] == ["CASE2", "CASE1"]
    assert snap["active"] == []


def test_environment_cost_includes_billed_searches() -> None:
    single = response("q", "a", cost=0.002)
    single.retriever_parameters = {
        "multi_part": False,
        "per_source": {"openrouter_search": {"query_attempts": [{"cost_usd": 0.007}]}},
    }
    assert environment_cost(single) == pytest.approx(0.009)
    multi = response("q", "a", cost=0.0)
    multi.retriever_parameters = {
        "multi_part": True,
        "sub_queries": [
            {"per_source": {"openrouter_search": {"query_attempts": [{"cost_usd": 0.007}]}}},
            {"per_source": {"europe_pmc": {"query_attempts": [{"returned": 3}]}}},
        ],
    }
    assert environment_cost(multi) == pytest.approx(0.007)


def test_end_to_end_with_the_medsim_environment_and_basic_strategy(tmp_path: Path) -> None:
    """The real MedicalEnvironment and basic strategy, one case, with scripted LLM replies."""
    settings = make_settings()
    llm = ScriptedLLM()
    config = make_config(
        write_cases(tmp_path), strategies=["basic"], max_cases=1, stopping={"max_iterations": 2}
    )
    for n, answer in enumerate(["She has a fever.", "It started two days ago."], 1):
        llm.push(
            {"question": f"Question {n}?", "rationale": "Most useful next."},
            resolver(True, answer, [f"span {n}"]),
        )
    factory = MedsimEnvironmentFactory(settings, llm)
    runner = ExperimentRunner(
        config,
        settings=settings,
        llm=llm,
        environment_factory=factory,
        strategies={"basic": build_strategy("basic", {}, llm=llm, settings=settings)},
    )
    record = runner.run()
    factory.close()

    run = record.case_runs[0]
    assert run.status == "completed", run.error
    assert [(it.question, it.answer, it.answer_source) for it in run.iterations] == [
        ("Question 1?", "She has a fever.", "case_study"),
        ("Question 2?", "It started two days ago.", "case_study"),
    ]
    assert run.iterations[0].strategy_llm_calls[0].stage == "strategy"
    response_1 = run.iterations[0].environment_response
    assert response_1 is not None and response_1.evidence == ["span 1"]
    assert llm.stages_called() == ["strategy", "resolver", "strategy", "resolver"]
    # the second strategy prompt carries the first answer; no prompt carries the diagnosis
    second_prompt = llm.calls[2]["messages"][1].content
    assert "Q: Question 1?\n   A: She has a fever." in second_prompt
    assert "Diagnosis 1" not in second_prompt
    strategy_prompts = [llm.calls[i]["messages"][1].content for i in (0, 2)]
    assert all("Diagnosis" not in p for p in strategy_prompts)
    saved = json.loads(Path(record.output).read_text(encoding="utf-8"))
    assert saved["case_runs"][0]["iterations"][1]["answer"] == "It started two days ago."


def test_medsim_factory_builds_a_fresh_environment_per_case_run() -> None:
    settings = make_settings()
    factory = MedsimEnvironmentFactory(settings, ScriptedLLM())
    case = CaseStudy(case_id="c", diagnosis="d", narrative="n")
    first, second = factory(case), factory(case)
    factory.close()
    assert isinstance(first, MedicalEnvironment)
    assert first.ledger is not second.ledger
    assert first.aggregator.retrievers[0] is not second.aggregator.retrievers[0]
    assert [r.name for r in first.aggregator.retrievers] == ["europe_pmc", "litsense"]


def test_basic_strategy_is_registered() -> None:
    settings = make_settings()
    strategy = build_strategy("basic", {"temperature": 0.5}, llm=ScriptedLLM(), settings=settings)
    assert isinstance(strategy, BasicStrategy)
    assert strategy.models() == [settings.default_model]
