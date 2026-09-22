from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from experiment.cli import ConsoleProgress, main
from experiment.config import ExperimentConfig
from experiment.runner import ExperimentListener, ExperimentRunner
from tests.conftest import ScriptedLLM, make_settings
from tests.experiment.helpers import FakeEnvironment, ScriptedStrategy, write_cases


def fake_runner(
    config: ExperimentConfig, *, listener: ExperimentListener, verify_models: bool | None
) -> ExperimentRunner:
    return ExperimentRunner(
        config,
        listener=listener,
        settings=make_settings(),
        llm=ScriptedLLM(),
        environment_factory=FakeEnvironment,
        strategies={key: ScriptedStrategy() for key in config.strategy_keys},
    )


def write_config(tmp_path: Path, **overrides: Any) -> Path:
    data = {
        "name": "cli",
        "cases_file": str(write_cases(tmp_path)),
        "strategies": ["basic"],
        "stopping": {"max_iterations": 5},
        "output": str(tmp_path / "records" / "{name}.json"),
    } | overrides
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_runs_the_config_with_command_line_overrides(tmp_path: Path) -> None:
    out, err = io.StringIO(), io.StringIO()
    code = main(
        ["--config", str(write_config(tmp_path)), "--max-cases", "2", "--max-iterations", "2"],
        runner_factory=fake_runner, stdout=out, stderr=err,
    )  # fmt: skip
    text = out.getvalue()
    assert code == 0, err.getvalue()
    assert 'Experiment "cli": 2 cases x 1 strategy (basic) = 2 case runs' in text
    assert "Each case run stops after 2 iterations" in text
    assert "[2/2] CASE2 · basic · 2 iterations · iteration limit" in text
    assert "Completed in" in text and "4 iterations, 0 errors" in text
    record = json.loads((tmp_path / "records" / "cli.json").read_text(encoding="utf-8"))
    assert record["config"]["stopping"]["max_iterations"] == 2


def test_configuration_errors_exit_with_2(tmp_path: Path) -> None:
    err = io.StringIO()
    path = write_config(tmp_path, case_ids=["NOPE"])
    code = main(["--config", str(path)], runner_factory=fake_runner, stdout=io.StringIO(),
                stderr=err)  # fmt: skip
    assert code == 2
    assert "NOPE" in err.getvalue()


def test_progress_bar_on_a_terminal() -> None:
    stream = io.StringIO()
    progress = ConsoleProgress(stream, live=True)
    assert progress.bar().startswith("[░░░")
    progress.stop()
    assert stream.getvalue() == "\r\033[K"


@pytest.mark.parametrize("seconds", [5, 65, 3700])
def test_durations(seconds: int) -> None:
    from experiment.cli import format_duration

    assert format_duration(seconds) == {5: "5s", 65: "1m 05s", 3700: "1h 01m"}[seconds]
