from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

from medsim.case_study import load_case_study
from medsim.cli import SYNTHESIZED_NOTE, EnvFactory, main
from medsim.environment import MedicalEnvironment
from medsim.errors import ConfigError, LLMError
from medsim.ledger import FactLedger
from medsim.models import EnvironmentResponse
from tests.conftest import FIXTURES, ScriptedLLM, make_settings
from tests.environment.test_environment import builder, docs_retrievers, resolver, synth

CASE = str(FIXTURES / "test_case.json")


def _factory(llm: ScriptedLLM) -> EnvFactory:
    def factory(args: argparse.Namespace) -> MedicalEnvironment:
        return MedicalEnvironment(
            case_study=load_case_study(args.case),
            llm=llm,
            retrievers=list(docs_retrievers()),
            settings=make_settings(),
        )

    return factory


def test_single_query_human_summary(llm: ScriptedLLM) -> None:
    llm.push(resolver(), builder(), synth())
    out, err = io.StringIO(), io.StringIO()
    code = main(
        ["--case", CASE, "--query", "What is the temperature on day 4?"],
        env_factory=_factory(llm),
        stdout=out,
        stderr=err,
    )
    assert code == 0, err.getvalue()
    text = out.getvalue()
    assert "A: Temperature is 38.1 °C." in text
    assert SYNTHESIZED_NOTE in text
    assert "literature query:" in text


def test_stdin_batch_shares_ledger_and_saves_it(llm: ScriptedLLM, tmp_path: Path) -> None:
    llm.push(resolver(), builder(), synth())
    ledger_path = tmp_path / "ledger.json"
    stdin = io.StringIO("What is the temperature on day 4?\n\ntemperature on day 4 in fahrenheit\n")
    out = io.StringIO()
    code = main(
        ["--case", CASE, "--json", "--save-ledger", str(ledger_path)],
        env_factory=_factory(llm),
        stdin=stdin,
        stdout=out,
        stderr=io.StringIO(),
    )
    assert code == 0
    lines = out.getvalue().splitlines()
    responses = [EnvironmentResponse.model_validate_json(line) for line in lines]
    assert len(responses) == 2
    assert responses[1].llm_calls == []
    assert responses[1].output_answer.endswith("(100.6 °F)")
    assert len(FactLedger.load(ledger_path)) == 1
    assert json.loads(ledger_path.read_text())["version"] == 2


def test_load_ledger_resumes_session(llm: ScriptedLLM, tmp_path: Path) -> None:
    llm.push(resolver(), builder(), synth())
    ledger_path = tmp_path / "ledger.json"
    first = ["--case", CASE, "--query", "temperature on day 4", "--save-ledger", str(ledger_path)]
    assert main(first, env_factory=_factory(llm), stdout=io.StringIO()) == 0

    out = io.StringIO()
    second = ["--case", CASE, "--query", "temperature on day 4", "--load-ledger", str(ledger_path)]
    assert main(second, env_factory=_factory(llm), stdout=out) == 0
    assert "llm calls: none" in out.getvalue()


def test_loaded_ledger_does_not_hit_for_a_different_case(llm: ScriptedLLM, tmp_path: Path) -> None:
    llm.push(resolver(), builder(), synth())
    ledger_path = tmp_path / "ledger.json"
    first = ["--case", CASE, "--query", "temperature on day 4", "--save-ledger", str(ledger_path)]
    assert main(first, env_factory=_factory(llm), stdout=io.StringIO()) == 0

    other_case = tmp_path / "other_case.json"
    other_case.write_text(
        json.dumps(json.loads(Path(CASE).read_text()) | {"case_id": "different-case"})
    )
    llm.push(resolver(), builder(), synth("Temperature is 37.2 °C.", value="37.2"))
    out = io.StringIO()
    second = [
        "--case", str(other_case), "--query", "temperature on day 4",
        "--load-ledger", str(ledger_path), "--save-ledger", str(ledger_path),
    ]  # fmt: skip
    assert main(second, env_factory=_factory(llm), stdout=out) == 0
    assert "A: Temperature is 37.2 °C." in out.getvalue()
    assert "llm calls: none" not in out.getvalue()
    assert sorted(FactLedger.load(ledger_path).case_ids) == ["different-case", "test-urti-001"]


def test_config_error_exit_code() -> None:
    def factory(args: argparse.Namespace) -> MedicalEnvironment:
        raise ConfigError("OPENROUTER_API_KEY is not set.")

    err = io.StringIO()
    code = main(["--case", CASE, "--query", "x"], env_factory=factory, stderr=err)
    assert code == 2
    assert "OPENROUTER_API_KEY is not set" in err.getvalue()


def test_query_error_continues_batch(llm: ScriptedLLM) -> None:
    llm.push(LLMError("upstream down"), resolver(True, "BP 118/76 mmHg.", ["118/76 mmHg"]))
    out, err = io.StringIO(), io.StringIO()
    code = main(
        ["--case", CASE],
        env_factory=_factory(llm),
        stdin=io.StringIO("first question\nWhat was the blood pressure?\n"),
        stdout=out,
        stderr=err,
    )
    assert code == 1
    assert "upstream down" in err.getvalue()
    assert "A: BP 118/76 mmHg." in out.getvalue()
