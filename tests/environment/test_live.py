"""Optional live integration test. Runs only with ``pytest --live`` and OPENROUTER_API_KEY set."""

from __future__ import annotations

import pytest

from medsim.config import load_settings
from medsim.environment import MedicalEnvironment
from tests.conftest import FIXTURES


@pytest.mark.live
def test_live_end_to_end() -> None:
    env = MedicalEnvironment.from_case_file(FIXTURES / "test_case.json", settings=load_settings())
    try:
        from_case = env.query("What was her blood pressure at presentation?")
        assert from_case.answer_source == "case_study"
        assert from_case.literature_search is False

        synthesized = env.query("What is the patient's heart rate?")
        assert synthesized.literature_search is True
        assert synthesized.answer_source in {"literature", "unanswerable"}
        assert synthesized.llm_calls

        repeat = env.query("What is the patient's heart rate?")
        assert repeat.output_answer == synthesized.output_answer or (
            synthesized.answer_source == "unanswerable"
        )
    finally:
        env.close()
