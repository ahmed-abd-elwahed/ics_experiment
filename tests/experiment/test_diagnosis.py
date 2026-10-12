"""The diagnosis step of a case run, and its evaluation by ICD-11 code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from evaluation.evaluate import evaluate_record, main, table
from evaluation.icd import SEARCH_URL, TOKEN_URL, ICDCoder, ICDError, normalize
from evaluation.metrics import case_scores, mean_scores, rank_of, ranked_codes
from experiment.record import load_record
from medsim.errors import LLMError
from medsim.models import LLMCallRecord
from strategies.base import CaseContext, Diagnosis, RankedDiagnosis
from tests.experiment.helpers import ScriptedSession, ScriptedStrategy
from tests.experiment.test_runner import runner_for


class DiagnosingSession(ScriptedSession):
    def final_diagnosis(self) -> Diagnosis:
        if self.strategy.prefix == "fail":
            raise LLMError("strategy: OpenRouter HTTP 502")
        call = LLMCallRecord(
            stage="strategy", model="test/strategy", prompt_tokens=20, completion_tokens=5,
            latency_ms=1.0, cost_usd=0.002,
        )  # fmt: skip
        guesses = [RankedDiagnosis("Diagnosis 1", 0.6), RankedDiagnosis("Diagnosis 2", 0.3)]
        return Diagnosis(guesses, [call], {"asked": len(self.memory)})


class DiagnosingStrategy(ScriptedStrategy):
    def new_session(self, context: CaseContext) -> DiagnosingSession:
        return DiagnosingSession(self, context)


def test_the_diagnosis_is_recorded_after_any_stop(tmp_path: Path) -> None:
    strategies = {"scripted": DiagnosingStrategy(stop_after=2)}
    runner, _ = runner_for(tmp_path, strategies=strategies, max_cases=1)
    run = runner.run().case_runs[0]

    assert run.stop_reason == "strategy_done"
    assert run.diagnosis is not None and run.diagnosis.error is None
    assert [(d.name, d.probability) for d in run.diagnosis.differential] == [
        ("Diagnosis 1", 0.6), ("Diagnosis 2", 0.3)
    ]  # fmt: skip
    assert run.diagnosis.trace == {"asked": 2}
    assert run.strategy_cost_usd == pytest.approx(2 * 0.0005 + 0.002)
    assert load_record(runner.prepare().output).case_runs[0].diagnosis == run.diagnosis


def test_a_failed_diagnosis_keeps_the_questions(tmp_path: Path) -> None:
    strategies = {"scripted": DiagnosingStrategy(prefix="fail")}
    runner, _ = runner_for(tmp_path, strategies=strategies, max_cases=1)
    record = runner.run()
    run = record.case_runs[0]

    assert (run.status, len(run.iterations)) == ("completed", 3)
    assert run.diagnosis is not None and run.diagnosis.differential == []
    assert run.diagnosis.error == "LLMError: strategy: OpenRouter HTTP 502"
    assert record.summary["overall"]["diagnosed"] == 0


def test_a_strategy_without_a_diagnosis_records_none(tmp_path: Path) -> None:
    runner, _ = runner_for(tmp_path, max_cases=1)
    assert runner.run().case_runs[0].diagnosis is None


# --- metrics ----------------------------------------------------------------------------------


def test_ranked_codes_keeps_the_best_score_per_code_and_drops_uncoded() -> None:
    predictions = [("A", 0.2), ("B", 0.5), ("", 0.9), ("A", 0.7), ("C", 0.5)]
    assert ranked_codes(predictions) == ["A", "B", "C"]


def test_scores_for_one_case() -> None:
    assert rank_of("B", ["A", "B"]) == 2
    assert rank_of("", ["A", ""]) is None  # an uncoded truth never matches
    assert rank_of("Z", ["A"]) is None
    scores = case_scores(2)
    assert (scores["hit_rate@1"], scores["hit_rate@2"], scores["hit_rate@10"]) == (0.0, 1.0, 1.0)
    assert scores["mrr"] == 0.5
    assert scores["ndcg@10"] == pytest.approx(0.6309, abs=1e-4)
    late = case_scores(11)
    assert (late["hit_rate@10"], late["ndcg@10"]) == (0.0, 0.0)
    assert late["mrr"] == pytest.approx(1 / 11)
    assert set(case_scores(None).values()) == {0.0}


def test_mean_scores_counts_misses() -> None:
    scores = mean_scores([1, None, 2, None])
    assert (scores["hit_rate@1"], scores["hit_rate@3"], scores["mrr"]) == (0.25, 0.5, 0.375)


# --- evaluating a record ------------------------------------------------------------------------

CODES = {"Diagnosis 1": "AA01", "Diagnosis 2": "BB02", "Diagnosis 3": ""}


def fake_coder(names: Any) -> list[str]:
    return [CODES[name] for name in names]


def test_evaluate_record_codes_ranks_and_averages(tmp_path: Path) -> None:
    strategies = {"scripted": DiagnosingStrategy()}
    runner, _ = runner_for(tmp_path, strategies=strategies, max_cases=3)
    evaluation = evaluate_record(runner.run(), fake_coder)

    rows = evaluation["case_runs"]
    assert [row["rank"] for row in rows] == [1, 2, None]  # case 3's diagnosis has no code
    assert rows[1]["true_icd_code"] == "BB02"
    assert rows[1]["predictions"][0] == {
        "name": "Diagnosis 1", "probability": 0.6, "icd_code": "AA01"
    }  # fmt: skip
    summary = evaluation["by_strategy"]["scripted"]
    assert summary["case_runs"] == 3
    assert summary["metrics"]["hit_rate@1"] == pytest.approx(1 / 3)
    assert summary["metrics"]["hit_rate@2"] == pytest.approx(2 / 3)
    assert summary["metrics"]["mrr"] == pytest.approx(0.5)
    assert summary["true_diagnosis_uncoded"] == 1
    assert evaluation["coding"]["names"] == 3
    assert "scripted" in table(evaluation)


def test_a_case_run_without_a_differential_scores_zero(tmp_path: Path) -> None:
    runner, _ = runner_for(tmp_path, max_cases=1)  # ScriptedStrategy gives no diagnosis
    summary = evaluate_record(runner.run(), fake_coder)["by_strategy"]["scripted"]
    assert summary["without_differential"] == 1
    assert summary["metrics"]["hit_rate@10"] == 0.0


# --- the ICD API --------------------------------------------------------------------------------


def coder(tmp_path: Path, **kwargs: Any) -> ICDCoder:
    return ICDCoder(
        "id", "secret", cache_path=tmp_path / "icd.json", sleep=lambda _: None, **kwargs
    )


def found(code: str) -> httpx.Response:
    return httpx.Response(200, json={"destinationEntities": [{"theCode": code}, {"theCode": "X"}]})


def test_normalize() -> None:
    assert normalize("  Long  QT\nSyndrome. ") == "long qt syndrome"


@respx.mock
def test_codes_are_looked_up_once_and_cached(tmp_path: Path) -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "tok"}))
    search = respx.get(SEARCH_URL)
    search.mock(side_effect=lambda request: (
        found("BC65.0") if request.url.params["q"] == "Long QT Syndrome"
        else httpx.Response(200, json={"destinationEntities": []})
    ))  # fmt: skip
    icd = coder(tmp_path, workers=2)

    assert icd.codes(["Long QT Syndrome", "long qt syndrome.", "", "Nonsense"]) == [
        "BC65.0", "BC65.0", "", ""
    ]  # fmt: skip
    assert search.call_count == 2
    request = search.calls[0].request
    assert request.headers["Authorization"] == "Bearer tok"
    assert request.headers["API-Version"] == "v2"
    assert request.url.params["useFlexisearch"] == "true"
    assert json.loads((tmp_path / "icd.json").read_text()) == {
        "long qt syndrome": "BC65.0", "nonsense": ""
    }  # fmt: skip
    assert coder(tmp_path).codes(["Nonsense", "Long QT syndrome"]) == ["", "BC65.0"]
    assert search.call_count == 2  # the second coder read the cache file


@respx.mock
def test_an_expired_token_is_refreshed(tmp_path: Path) -> None:
    token = respx.post(TOKEN_URL).mock(
        side_effect=[httpx.Response(200, json={"access_token": t}) for t in ("old", "new")]
    )
    respx.get(SEARCH_URL).mock(side_effect=[httpx.Response(401), found("1A00")])
    assert coder(tmp_path).codes(["Cholera"]) == ["1A00"]
    assert token.call_count == 2


@respx.mock
def test_a_failed_lookup_is_not_cached(tmp_path: Path) -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "tok"}))
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(ICDError, match="1 of 1 ICD lookups failed"):
        coder(tmp_path, max_retries=1).codes(["Cholera"])
    assert json.loads((tmp_path / "icd.json").read_text()) == {}


def test_cli_needs_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner, _ = runner_for(tmp_path, max_cases=1)
    record = runner.run()
    monkeypatch.chdir(tmp_path)  # no .env here
    monkeypatch.delenv("ICD_CLIENT_ID", raising=False)
    monkeypatch.delenv("ICD_CLIENT_SECRET", raising=False)
    assert main([record.output]) == 1
    assert "ICD_CLIENT_ID and ICD_CLIENT_SECRET are not set" in capsys.readouterr().err
