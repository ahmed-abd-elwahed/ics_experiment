"""The new answer metrics: the code around the judges (no LLM calls)."""

from __future__ import annotations

from typing import Any

import pytest

from bench.answer_metrics import (
    AlignmentLevelOutput,
    AlignmentOutput,
    FaithfulnessOutput,
    Reference,
    ReferenceOutput,
    alignment_label,
    combine_reference,
    eligible,
    judge_alignment,
    judge_faithfulness,
    scorable,
    value_score,
)
from bench.judge import Judge
from bench.schemas import DocRecord, Item, RunRecord, Truth
from medsim.models import CaseStudy, LLMCallRecord

CASE = CaseStudy(
    case_id="c1",
    diagnosis="Sepsis",
    narrative="A 60-year-old man. The metabolic panel was unremarkable. He was afebrile.",
)


def item(question_set: str = "A", truth: Truth | None = None) -> Item:
    return Item(
        item_id=f"{question_set}:c1:sodium", question_set=question_set, case_id="c1",  # type: ignore[arg-type]
        diagnosis="Sepsis", question="What is the serum sodium?", variable="serum sodium",
        category="laboratory", truth=truth, case=CASE, patient="A 60-year-old man.",
    )  # fmt: skip


def run(
    config: str = "current", documents: bool = True, answer: str | None = "Sodium is 140."
) -> RunRecord:
    docs = [DocRecord(rank=1, source="s", doc_id="d1", title="Sodium in sepsis",
                      text="Serum sodium ranged from 134 to 142 mmol/L.")]  # fmt: skip
    return RunRecord(
        item_id="A:c1:sodium", config=config, question_set="A", status="ok",
        started_at="2026-10-13T00:00:00+00:00", wall_time_s=1.0, answer_source="literature",
        output_answer=answer, documents=docs if documents else [],
    )  # fmt: skip


class StubJudge(Judge):
    """A judge whose reply is fixed."""

    def __init__(self, reply: Any) -> None:
        super().__init__(llm=None, model="stub/judge", max_tokens=100)  # type: ignore[arg-type]
        self._reply = reply

    def _call(self, messages: Any, output: Any, records: list[LLMCallRecord]) -> Any:
        return self._reply


def ref(**kw: Any) -> ReferenceOutput:
    base = {"numeric": True, "truth_low": 2.6, "truth_high": 2.6, "reference_lower": 0.6,
            "reference_upper": 1.2, "note": ""}  # fmt: skip
    return ReferenceOutput(**(base | kw))


def test_reference_is_the_median_of_the_judges() -> None:
    combined = combine_reference([ref(reference_upper=1.1), ref(), ref(reference_upper=1.3)])
    assert combined == Reference(True, 2.6, 2.6, 0.6, 1.2, 3)


def test_a_limit_most_judges_leave_out_is_left_out() -> None:
    combined = combine_reference(
        [ref(reference_lower=None), ref(reference_lower=None), ref(reference_lower=0.5)]
    )
    assert combined is not None and combined.lower is None and combined.upper == 1.2


def test_non_numeric_true_values_are_not_scored() -> None:
    finding = combine_reference([ref(numeric=False, truth_low=None, truth_high=None)] * 2 + [ref()])
    assert not scorable(finding)
    assert scorable(combine_reference([ref()]))
    assert not scorable(None)


def test_value_score() -> None:
    reference = Reference(True, 2.6, 2.6, 0.6, 1.2, 3)
    exact = {"comparable": True, "answer_low": 2.6, "answer_high": 2.6}
    off = {"comparable": True, "answer_low": 2.0, "answer_high": 2.0}
    assert value_score(reference, exact) == 0.0
    assert value_score(reference, off) == pytest.approx(1.48, abs=0.01)
    assert value_score(reference, {"comparable": False, "answer_low": None}) == 3.0
    assert (
        value_score(reference, {"comparable": True, "answer_low": 260.0, "answer_high": 260.0})
        == 3.0
    )


def test_faithfulness_needs_a_quote_that_is_in_the_documents() -> None:
    found = FaithfulnessOutput(supported=True, quote="ranged from 134 to 142 mmol/L", rationale="")
    invented = FaithfulnessOutput(
        supported=True, quote="sodium was 140 in all patients", rationale=""
    )
    declined = FaithfulnessOutput(supported=False, quote="", rationale="")
    labels = [
        judge_faithfulness(StubJudge(reply), item(), run()).output
        for reply in (found, invented, declined)
    ]
    assert [o["label"] for o in labels if o] == ["supported", "not_supported", "not_supported"]
    assert [o["quote_ok"] for o in labels if o] == [True, False, None]


def test_alignment_without_a_quote_from_the_case_is_neutral() -> None:
    aligned = AlignmentOutput(
        label="aligned", quote="metabolic panel was unremarkable", rationale=""
    )
    unfounded = AlignmentOutput(label="contradicted", quote="sodium was 120", rationale="")
    outputs = [
        judge_alignment(StubJudge(reply), item("B"), CASE, run(), "m1").output
        for reply in (aligned, unfounded)
    ]
    assert [o["label"] for o in outputs if o] == ["aligned", "neutral"]
    assert [o["label_raw"] for o in outputs if o] == ["aligned", "contradicted"]


def test_which_answers_get_a_judge_call() -> None:
    a, b, c = item("A", Truth(value="140", unit="mmol/L", span="140")), item("B"), item("C")
    assert eligible("faithfulness", a, run()) and eligible("faithfulness", b, run())
    assert not eligible("faithfulness", c, run())
    assert not eligible("faithfulness", a, run(config="gemini_knowledge"))
    assert not eligible("faithfulness", a, run(documents=False))
    assert not eligible("faithfulness", a, run(answer=None))
    assert eligible("zlog_value", a, run()) and not eligible("zlog_value", b, run())
    assert eligible("case_alignment", b, run()) and not eligible("case_alignment", a, run())
    assert eligible("masked_correctness", a, run()) and not eligible("masked_correctness", b, run())
    assert eligible("factual_consistency", b, run()) and not eligible(
        "factual_consistency", a, run()
    )


def test_revised_alignment_compares_the_expected_level_with_the_answers() -> None:
    assert alignment_label("normal", "normal") == "aligned"
    assert alignment_label("high", "normal") == "contradicted"
    assert alignment_label("none", "normal") == "neutral"
    assert alignment_label("normal", "unclear") == "neutral"
    grounded = AlignmentLevelOutput(
        expected="normal", answer="low", quote="metabolic panel was unremarkable", rationale=""
    )
    invented = AlignmentLevelOutput(
        expected="low", answer="low", quote="sodium was low on admission", rationale=""
    )
    outputs = [
        judge_alignment(StubJudge(reply), item("B"), CASE, run(), "m2")
        for reply in (grounded, invented)
    ]
    assert [o.output["label"] for o in outputs if o.output] == ["contradicted", "neutral"]
    assert [o.rubric for o in outputs] == ["m2", "m2"]
