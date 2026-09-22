from __future__ import annotations

import json
from pathlib import Path

import pytest

from medsim.ledger import FactLedger

CASE = "case-A"
OTHER = "case-B"


def _ledger_with_temperature() -> FactLedger:
    ledger = FactLedger()
    ledger.record(
        case_id=CASE,
        query="What is the patient's temperature on day 3?",
        answer="Temperature on day 3 is 37.0 °C.",
        answer_source="literature",
        clinical_variable="body temperature on day 3",
        value="37.0",
        unit="°C",
        source_doc_ids=["PMID:1"],
        evidence=["PMID:1", "literature range: 36.8-37.5 °C (PMID:1)"],
        confidence="medium",
    )
    return ledger


def test_repeat_query_returns_stored_answer_verbatim() -> None:
    ledger = _ledger_with_temperature()
    for paraphrase in (
        "What is the patient's temperature on day 3?",
        "temperature on day 3",
        "What was her body temperature on day 3?",
    ):
        fact = ledger.lookup(paraphrase, case_id=CASE)
        assert fact is not None
        assert fact.case_id == CASE
        assert ledger.render_answer(fact, paraphrase) == "Temperature on day 3 is 37.0 °C."


def test_different_timepoint_is_not_a_repeat() -> None:
    ledger = _ledger_with_temperature()
    assert ledger.lookup("What is the temperature on day 5?", case_id=CASE) is None
    assert ledger.lookup("What is the temperature?", case_id=CASE) is None


def test_same_question_for_another_case_is_not_a_hit() -> None:
    ledger = _ledger_with_temperature()
    query = "What is the patient's temperature on day 3?"
    assert ledger.lookup(query, case_id=OTHER) is None
    assert ledger.lookup(query, "body temperature on day 3", case_id=OTHER) is None

    ledger.record(
        case_id=OTHER, query=query, answer="Temperature on day 3 is 39.2 °C.",
        answer_source="literature", clinical_variable="body temperature on day 3",
        value="39.2", unit="°C",
    )  # fmt: skip
    fact_a = ledger.lookup(query, case_id=CASE)
    fact_b = ledger.lookup(query, case_id=OTHER)
    assert fact_a is not None and fact_a.value == "37.0"
    assert fact_b is not None and fact_b.value == "39.2"
    assert len(ledger) == 2
    assert sorted(ledger.case_ids) == [CASE, OTHER]


def test_prompt_block_only_lists_facts_for_that_case() -> None:
    ledger = _ledger_with_temperature()
    assert "temperature@day3" in ledger.prompt_block(CASE)
    assert ledger.prompt_block(OTHER) == "(none)"


def test_unit_conversion_never_disagrees() -> None:
    ledger = _ledger_with_temperature()
    query = "What is the patient's temperature on day 3 in Fahrenheit?"
    fact = ledger.lookup(query, case_id=CASE)
    assert fact is not None
    assert ledger.render_answer(fact, query) == "Temperature on day 3 is 37.0 °C. (98.6 °F)"
    # Asking in the stored unit gives the verbatim answer, not a second conversion.
    assert ledger.render_answer(fact, "temperature on day 3 in celsius") == fact.answer


def test_value_and_unit_parsed_from_case_answer() -> None:
    ledger = FactLedger()
    fact = ledger.record(
        case_id=CASE,
        query="What was the temperature at presentation?",
        answer="Her temperature at presentation was 37.9 °C.",
        answer_source="case_study",
    )
    assert (fact.value, fact.unit) == ("37.9", "°C")
    assert fact.clinical_variable == "temperature@admission"
    rendered = ledger.render_answer(fact, "temperature at presentation in °F")
    assert rendered.endswith("(100.2 °F)")


def test_lookup_by_stage_b_variable() -> None:
    ledger = FactLedger()
    ledger.record(
        case_id=CASE,
        query="How fast is she breathing?",
        answer="Respiratory rate is 16 breaths/min.",
        answer_source="literature",
        clinical_variable="respiratory rate",
        value="16",
        unit="breaths/min",
    )
    assert ledger.lookup("How fast is she breathing?", case_id=CASE) is not None
    assert ledger.lookup("What's the breathing pace?", case_id=CASE) is None
    assert ledger.lookup("What's the breathing pace?", "respiratory rate", case_id=CASE) is not None


def test_reset_one_case_or_all() -> None:
    ledger = _ledger_with_temperature()
    ledger.record(
        case_id=OTHER, query="temperature on day 3", answer="Temperature is 38.0 °C.",
        answer_source="literature",
    )  # fmt: skip
    ledger.reset(OTHER)
    assert ledger.case_ids == [CASE]
    assert ledger.lookup("temperature on day 3", case_id=CASE) is not None
    ledger.reset()
    assert len(ledger) == 0


def test_serialization_roundtrip_keeps_case_ids(tmp_path: Path) -> None:
    ledger = _ledger_with_temperature()
    path = tmp_path / "ledger.json"
    ledger.save(path)
    saved = json.loads(path.read_text())
    assert saved["version"] == 2
    assert saved["cases"][CASE]["facts"]["temperature@day3"]["case_id"] == CASE

    restored = FactLedger.load(path)
    assert restored.facts == ledger.facts
    assert restored.lookup("temperature on day 3", case_id=CASE) is not None
    assert restored.lookup("temperature on day 3", case_id=OTHER) is None


def test_version_1_ledger_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"version": 1, "facts": {}, "queries": {}}))
    with pytest.raises(ValueError, match="version 1 is not supported"):
        FactLedger.load(path)
