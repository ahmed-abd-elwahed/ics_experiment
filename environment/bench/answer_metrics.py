"""Three more metrics on medsim's generated answers, and the Jev decision model as a judge.

- **zlog z-score** (sets A and C): how far the answer's value is from the true value, on the
  zlog scale (``bench.zlog``). The judges only read numbers: once per question the reference
  limits and the true value, once per answer the answer's value. Code computes z.
- **faithfulness** (sets A and B): do the retrieved documents support the answer's value? Yes
  or no, with a verbatim quote that code looks for in the documents.
- **case alignment** (sets B and C): aligned, neutral, or contradicted, against the rest of the
  case, with a verbatim quote that code looks for in the case.

Every judgment is one record in ``<workspace>/judge/<metric>.jsonl``; the reference limits are
shared by all runs (the questions are the same) and live in one file. Jobs already done are
skipped, so a rerun retries only the failed ones.

``typesafe/jev-1.13`` is a decision model: it returns a typed choice with probabilities through
OpenRouter's decisions endpoint, and no text. It can therefore give the two existing metrics'
labels, faithfulness, and case alignment, but it cannot quote a passage or read out a number.

Usage: python -m bench.answer_metrics --runs 2 --metrics faithfulness --judges MODEL[,MODEL]
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from bench.config import BenchSettings
from bench.judge import (
    CASE_CORRECTNESS_PROMPT,
    FACTUAL_CONSISTENCY_PROMPT,
    FACTUAL_CONSISTENCY_PROMPT_C,
    MASKED_CORRECTNESS_PROMPT,
    RUBRIC,
    SET_METRICS,
    Judge,
    _full_case,
    _target,
    _truth,
    answer_key,
    full_cases,
    judgeable,
    latest_runs,
    ok_judgments,
)
from bench.schemas import (
    ConsistencyJudgment,
    ConsistencyOutput,
    Item,
    MaskedCorrectnessJudgment,
    MaskedCorrectnessOutput,
    RunRecord,
    Status,
    _AnswerJudgment,
    _LLMOutput,
    calls_cost,
)
from bench.text import load_cases, quote_found
from bench.workspace import JsonlWriter, Workspace, read_jsonl, read_models
from bench.zlog import SCORE_CAP, zlog_score_truth_range
from medsim.config import Settings, load_settings
from medsim.errors import MedSimError
from medsim.llm.openrouter import OpenRouterClient
from medsim.models import CaseStudy, ChatMessage, LLMCallRecord

logger = logging.getLogger("bench.answer_metrics")

METRIC_RUBRIC = "m1"
JEV_MODEL = "typesafe/jev-1.13"
RESULTS = Path(__file__).resolve().parents[1] / "results"
REPO = RESULTS.parents[1]
SHARED = RESULTS / "answer_metrics"
REFERENCE_FILE = SHARED / "zlog_reference.jsonl"
# No retrieved documents to be faithful to: the one "document" is the model's own statement.
NO_DOCUMENT_CONFIGS = frozenset({"gemini_knowledge", "case_information"})
NEW_METRICS = ("zlog_value", "faithfulness", "case_alignment")
METRIC_SETS: dict[str, tuple[str, ...]] = {
    "zlog_value": ("A", "C"),
    "faithfulness": ("A", "B"),
    "case_alignment": ("B", "C"),
}


# --- what the judges return ----------------------------------------------------------------------


class ReferenceOutput(_LLMOutput):
    numeric: bool
    truth_low: float | None
    truth_high: float | None
    reference_lower: float | None
    reference_upper: float | None
    note: str


class ValueOutput(_LLMOutput):
    comparable: bool
    answer_low: float | None
    answer_high: float | None
    note: str


class FaithfulnessOutput(_LLMOutput):
    supported: bool
    quote: str
    rationale: str


class AlignmentOutput(_LLMOutput):
    label: Literal["aligned", "neutral", "contradicted"]
    quote: str
    rationale: str


Level = Literal["low", "normal", "high", "present", "absent", "none"]
AnswerLevel = Literal["low", "normal", "high", "present", "absent", "unclear"]


class AlignmentLevelOutput(_LLMOutput):
    """The revised case alignment (rubric m2): two readings instead of one verdict."""

    expected: Level
    answer: AnswerLevel
    quote: str
    rationale: str


class ReferenceJudgment(BaseModel):
    """One judge's reference limits and reading of the true value, for one question."""

    item_id: str
    judge_model: str
    rubric: str
    status: Status
    error: str | None = None
    output: ReferenceOutput | None = None
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


class MetricJudgment(_AnswerJudgment):
    """One judge's judgment of one answer under one of the new metrics.

    ``output`` is the judge's reply plus what code derived from it: ``quote_ok`` and the final
    ``label`` for faithfulness and case alignment.
    """

    metric: str
    output: dict[str, Any] | None = None


# --- prompts -------------------------------------------------------------------------------------

REFERENCE_PROMPT = """\
You prepare a numeric comparison for one clinical variable of one patient. You see the QUESTION, \
the TRUE VALUE as the case report states it, its UNIT, and a short PATIENT description. Give \
every number in that UNIT.

Fields:
- numeric: true if the TRUE VALUE is a number, a numeric range, or a numeric bound on a \
measurement scale; false for a finding or a grade ("positive", "3+", "diminished").
- truth_low, truth_high: the TRUE VALUE as numbers. A single value: both the same. A range \
("60-70"): its ends. A bound: "> 1000" is truth_low 1000 and truth_high null; "< 5" is \
truth_low null and truth_high 5. For blood pressure use the systolic value. Null for both if \
not numeric.
- reference_lower, reference_upper: the usual reference limits of this variable for this kind \
of patient (age, sex, pregnancy), in the same UNIT; for blood pressure, of the systolic value. \
Use null for a limit that does not exist (a one-sided range such as "< 5" has reference_lower \
null). Use null for both if the variable has no accepted reference interval (a lesion size, a \
dose, an age, a count of events).
- note: a few words, e.g. the source of the limits.
Return only a JSON object with exactly these keys."""

VALUE_PROMPT = """\
A patient simulator answered a question about a patient. Read the number the SIMULATED ANSWER \
states for the TARGET VARIABLE and give it in the TARGET UNIT, converting when the answer uses \
another unit. Do not judge whether it is right.

Fields:
- comparable: false if the answer states no number for this variable (only a direction or a \
finding, another variable, or a unit that cannot be converted); otherwise true.
- answer_low, answer_high: the value in the TARGET UNIT. A single value: both the same. A range: \
its ends. A bound ("> 1000"): the bound for both. For blood pressure use the systolic value. \
Null for both if not comparable. If no TARGET UNIT is given, keep the answer's own number.
- note: a few words, e.g. the conversion used.
Return only a JSON object with exactly these keys."""

FAITHFULNESS_PROMPT = """\
A patient simulator answered a question about a patient after retrieving documents from the \
literature. You see the QUESTION, the DIAGNOSIS, a short PATIENT description, the SIMULATED \
ANSWER, and the RETRIEVED DOCUMENTS. Decide whether the documents support the value the answer \
states. Judge only from the documents, not from what you know.

Fields:
- supported: true if at least one document gives a value, a range, or an explicit level \
("normal", "markedly elevated") for the same variable, in a comparable patient (this or a \
closely related condition, or a reference range that applies to such a patient), and that \
agrees with the answer's value. false if the documents only mention the variable without a \
value, give values that disagree with the answer, or concern another variable or a clearly \
different population.
- quote: when supported, the one passage that shows it, copied exactly from a document (at most \
40 words, no ellipsis); "" when not supported.
- rationale: one sentence.
Return only a JSON object with exactly these keys."""

ALIGNMENT_PROMPT = """\
A patient simulator answered a question about a patient. You see the QUESTION, the DIAGNOSIS, \
the FULL CASE REPORT, and the SIMULATED ANSWER. Decide how the rest of the case report bears on \
the value or finding the answer states.

Fields:
- label: "aligned" = a statement in the case report implies the answer: it states this value \
or finding, describes the variable's level, covers it in a panel or examination reported as \
normal or abnormal, or describes a clinical state that determines it, and the answer matches; \
"neutral" = nothing in the case report bears on this variable, so the answer can neither be \
confirmed nor refuted from it; "contradicted" = a statement in the case report conflicts with \
the answer.
- quote: for aligned or contradicted, the one passage of the case report that shows it, copied \
exactly (at most 40 words, no ellipsis); "" for neutral.
- rationale: one sentence.
Judge only from the case report. Return only a JSON object with exactly these keys."""

# Rubric m2. The first version asked for one verdict and let only explicit statements count;
# 96% of set B answers came back neutral. This one lets the clinical picture set an expectation
# and has the judge read two levels, which code compares.
ALIGNMENT_LEVEL_PROMPT = """\
A patient simulator answered a question about a patient. You see the QUESTION, the DIAGNOSIS, \
the FULL CASE REPORT, and the SIMULATED ANSWER. Read two things; do not judge the answer.

Fields:
- expected: the level of the TARGET VARIABLE that the rest of the case report leads a clinician \
to expect for this patient at this time: "low", "normal", or "high" relative to the usual \
reference range for such a patient (for a finding or a history item: "present" or "absent"). \
Base it on what the case report says: a statement about the variable, a panel, examination or \
organ system reported as normal or abnormal, the patient's described state (stable, febrile, \
in shock, bleeding, dehydrated), treatments, and the course of the illness. Use "none" when the \
case report gives no reason to expect one level over another; a diagnosis unrelated to the \
variable, with nothing else bearing on it, is "none".
- answer: the level the SIMULATED ANSWER states, on the same scale ("low", "normal", "high", \
"present", "absent"); "unclear" if it states none.
- quote: the one passage of the case report that grounds the expectation, copied exactly (at \
most 40 words, no ellipsis); "" when expected is "none".
- rationale: one sentence.
Return only a JSON object with exactly these keys."""

_LEVELS = {
    "low": "Below the usual reference range for such a patient.",
    "normal": "Within the usual reference range for such a patient.",
    "high": "Above the usual reference range for such a patient.",
    "present": "A finding or history item that is present.",
    "absent": "A finding or history item that is absent.",
}
JEV_LEVEL_QUESTIONS: dict[str, dict[str, Any]] = {
    "expected": {
        "type": "choice",
        "instructions": "Which level of the target variable does the rest of the case report "
        "lead a clinician to expect for this patient at this time? Base it on what the case "
        "report says: statements about the variable, panels, examinations or organ systems "
        "reported as normal or abnormal, the patient's described state, treatments, and the "
        "course of the illness.",
        "criteria": _LEVELS
        | {"none": "The case report gives no reason to expect one level over another."},
    },
    "answer": {
        "type": "choice",
        "instructions": "Which level of the target variable does the simulated answer state?",
        "criteria": _LEVELS | {"unclear": "The answer states no level."},
    },
}


def alignment_label(expected: str, answer: str) -> str:
    """Aligned when the answer's level is the expected one; neutral without an expectation."""
    if expected == "none" or answer == "unclear":
        return "neutral"
    return "aligned" if expected == answer else "contradicted"


# The decision model takes instructions and one definition per option instead of a prompt.
JEV_QUESTIONS: dict[str, dict[str, Any]] = {
    "masked_correctness": {
        "type": "choice",
        "instructions": MASKED_CORRECTNESS_PROMPT.split("\n\nFields:")[0] + " Convert units "
        "when needed.",
        "criteria": {
            "exact": "The true value lies inside the range the answer states, or the answer "
            "states a single value that is clinically the same finding as the true value "
            "(within about 10-15% or the measurement's usual variability).",
            "same_category": "Not exact, but the answer implies the same category (low / "
            "normal / high) as the true value, including an answer that gives only a matching "
            "direction.",
            "different_category": "The answer implies a different category than the true value.",
            "not_comparable": "The answer gives no value or direction for this variable, gives "
            "another variable, or uses units that cannot be converted.",
        },
    },
    "masked_correctness_c": {
        "type": "choice",
        "instructions": CASE_CORRECTNESS_PROMPT.split("\n\nFields:")[0] + " Convert units "
        "when needed.",
        "criteria": {
            "exact": "The answer states the true answer: the same value (a stated range that "
            "contains it, or a single value within about 10-15% or the measurement's usual "
            "variability), or the same finding with the details that matter clinically.",
            "same_category": "Not exact, but consistent with it: the same category (low / "
            "normal / high) for a measurement, or the same finding with a wrong or missing "
            "detail that does not change its meaning.",
            "different_category": "The answer contradicts the true answer: another category, a "
            "finding the case reports as absent, or the reverse.",
            "not_comparable": "The answer does not address this question.",
        },
    },
    "factual_consistency": {
        "type": "choice",
        "instructions": FACTUAL_CONSISTENCY_PROMPT.split("\n\nFields:")[0] + " Judge only "
        "against the case report and established physiology; do not require the answer to "
        "match the value you would have guessed.",
        "criteria": {
            "consistent": "Nothing in the case report contradicts the answer, and the answer "
            "is physiologically plausible for this patient given the diagnosis, findings, "
            "treatments, and timeline, even if it is not the most typical value.",
            "inconsistent": "The answer contradicts something the case report states, or it "
            "is implausible for this patient given the diagnosis and findings.",
        },
    },
    "faithfulness": {
        "type": "noul",
        "instructions": "A patient simulator answered a question about a patient after "
        "retrieving documents from the literature. Is the value the simulated answer states "
        "supported by the retrieved documents? Yes only if at least one document gives a "
        "value, a range, or an explicit level for the same variable, in a comparable patient "
        "(this or a closely related condition, or a reference range that applies to such a "
        "patient), that agrees with the answer's value. No if the documents only mention the "
        "variable without a value, give values that disagree, or concern another variable or "
        "a clearly different population. Judge only from the documents.",
    },
    "case_alignment": {
        "type": "choice",
        "instructions": ALIGNMENT_PROMPT.split("\n\nFields:")[0] + " Judge only from the case "
        "report.",
        "criteria": {
            "aligned": "A statement in the case report implies the answer: it states this "
            "value or finding, describes the variable's level, covers it in a panel or "
            "examination reported as normal or abnormal, or describes a clinical state that "
            "determines it, and the answer matches.",
            "neutral": "Nothing in the case report bears on this variable, so the answer can "
            "neither be confirmed nor refuted from it.",
            "contradicted": "A statement in the case report conflicts with the answer.",
        },
    },
}
JEV_QUESTIONS["factual_consistency_c"] = JEV_QUESTIONS["factual_consistency"] | {
    "instructions": FACTUAL_CONSISTENCY_PROMPT_C.split("\n\nFields:")[0]
    + " Judge only against the case report and established physiology."
}


def documents_text(run: RunRecord) -> str:
    """The retrieved documents as Stage C saw them, numbered."""
    return "\n\n".join(
        f"[{doc.rank}] {doc.title or '(no title)'}\n{doc.text}" for doc in run.documents
    )


def _messages(system: str, user: str) -> list[ChatMessage]:
    return [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)]


def reference_messages(item: Item) -> list[ChatMessage]:
    assert item.truth is not None
    return _messages(
        REFERENCE_PROMPT,
        f"QUESTION: {item.question}\nTARGET VARIABLE: {_target(item)}\n"
        f'TRUE VALUE: {item.truth.value} (case report: "{item.truth.span}")\n'
        f"UNIT: {item.truth.unit or '(not stated; use the unit the case report implies)'}\n"
        f"DIAGNOSIS: {item.diagnosis}\nPATIENT: {item.patient}",
    )


def value_messages(item: Item, answer: str) -> list[ChatMessage]:
    unit = item.truth.unit if item.truth and item.truth.unit else "(none given)"
    return _messages(
        VALUE_PROMPT,
        f"QUESTION: {item.question}\nTARGET VARIABLE: {_target(item)}\nTARGET UNIT: {unit}\n\n"
        f"SIMULATED ANSWER: {answer}",
    )


def faithfulness_messages(item: Item, run: RunRecord) -> list[ChatMessage]:
    return _messages(
        FAITHFULNESS_PROMPT,
        f"QUESTION: {item.question}\nTARGET VARIABLE: {_target(item)}\n"
        f"DIAGNOSIS: {item.diagnosis}\nPATIENT: {item.patient}\n\n"
        f"SIMULATED ANSWER: {run.output_answer}\n\nRETRIEVED DOCUMENTS:\n{documents_text(run)}",
    )


def alignment_messages(item: Item, case: CaseStudy, answer: str) -> list[ChatMessage]:
    return _messages(
        ALIGNMENT_PROMPT,
        f"QUESTION: {item.question}\nTARGET VARIABLE: {_target(item)}\n"
        f"DIAGNOSIS: {case.diagnosis}\n\nFULL CASE REPORT:\n{_full_case(case)}\n\n"
        f"SIMULATED ANSWER: {answer}",
    )


# --- the decision model --------------------------------------------------------------------------


class JevClient:
    """``POST /api/alpha/decisions``: one item and its typed questions per request."""

    def __init__(
        self, settings: Settings, *, model: str = JEV_MODEL, max_attempts: int = 5
    ) -> None:
        self.model = model
        self._key = settings.openrouter_api_key.get_secret_value()
        self._url = settings.openrouter_base_url.rstrip("/").removesuffix("/v1") + (
            "/alpha/decisions"
        )
        self._client = httpx.Client(timeout=60.0)
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._client.close()

    def decide(
        self, state: Mapping[str, str], question: Mapping[str, Any], records: list[LLMCallRecord]
    ) -> dict[str, Any]:
        """The answer to one question about ``state``; every attempt is appended to ``records``."""
        return self.decide_all(state, {"q": question}, records)["q"]

    def decide_all(
        self,
        state: Mapping[str, str],
        questions: Mapping[str, Mapping[str, Any]],
        records: list[LLMCallRecord],
    ) -> dict[str, dict[str, Any]]:
        """The answers to several questions about ``state``, in one request."""
        body = {"model": self.model, "state": dict(state),
                "questions": {name: dict(q) for name, q in questions.items()}}  # fmt: skip
        error = "no attempt made"
        for attempt in range(1, self._max_attempts + 1):
            started = time.perf_counter()
            status = 0
            data: dict[str, Any] = {}
            try:
                response = self._client.post(
                    self._url, headers={"Authorization": f"Bearer {self._key}"}, json=body
                )
                status = response.status_code
                data = response.json() if status < 500 else {}
            except (httpx.HTTPError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"[:300]
            latency = (time.perf_counter() - started) * 1000
            usage = data.get("usage") or {}
            answer = data.get("answers")
            ok = (
                status == 200
                and isinstance(answer, dict)
                and all(isinstance(answer.get(name), dict) for name in questions)
            )
            if status and not ok:
                error = f"Jev HTTP {status}: {json.dumps(data)[:300]}"
            records.append(
                LLMCallRecord(
                    stage="judge", model=self.model, prompt_tokens=usage.get("input_tokens"),
                    completion_tokens=usage.get("output_tokens"), latency_ms=latency,
                    attempt=attempt, success=ok, error=None if ok else error,
                    cost_usd=usage.get("cost"),
                )
            )  # fmt: skip
            if ok and isinstance(answer, dict):
                return answer
            if status in (400, 401, 402, 403, 404, 413, 422):
                break
            time.sleep(min(30.0, 2.0 ** (attempt - 1)))
        raise MedSimError(error)


def _jev_label(answer: Mapping[str, Any]) -> str:
    return str(answer["choice"])


def _jev_note(answer: Mapping[str, Any]) -> str:
    return json.dumps(
        {k: answer[k] for k in ("probabilities", "confidence", "noul") if k in answer},
        sort_keys=True,
    )


# --- one judgment --------------------------------------------------------------------------------

AnyJudge = Judge | JevClient


def _base(model: str, item: Item, config: str, answer: str, rubric: str) -> dict[str, Any]:
    return {"item_id": item.item_id, "config": config, "judge_model": model, "rubric": rubric,
            "answer_key": answer_key(item.item_id, config, answer)}  # fmt: skip


def judge_reference(judge: Judge, item: Item) -> ReferenceJudgment:
    records: list[LLMCallRecord] = []
    base: dict[str, Any] = {
        "item_id": item.item_id, "judge_model": judge.model, "rubric": METRIC_RUBRIC
    }  # fmt: skip
    try:
        out: ReferenceOutput = judge._call(reference_messages(item), ReferenceOutput, records)
    except MedSimError as exc:
        return ReferenceJudgment(**base, status="error", error=str(exc)[:300], llm_calls=records)
    return ReferenceJudgment(**base, status="ok", output=out, llm_calls=records)


def _metric_record(
    base: dict[str, Any],
    metric: str,
    records: list[LLMCallRecord],
    fn: Callable[[], dict[str, Any]],
) -> MetricJudgment:
    try:
        output = fn()
    except MedSimError as exc:
        return MetricJudgment(
            **base, metric=metric, status="error", error=str(exc)[:300], llm_calls=records
        )
    return MetricJudgment(**base, metric=metric, status="ok", output=output, llm_calls=records)


def judge_value(judge: Judge, item: Item, run: RunRecord) -> MetricJudgment:
    answer = run.output_answer or ""
    records: list[LLMCallRecord] = []

    def call() -> dict[str, Any]:
        out: ValueOutput = judge._call(value_messages(item, answer), ValueOutput, records)
        return out.model_dump()

    base = _base(judge.model, item, run.config, answer, METRIC_RUBRIC)
    return _metric_record(base, "zlog_value", records, call)


def judge_faithfulness(judge: AnyJudge, item: Item, run: RunRecord) -> MetricJudgment:
    answer = run.output_answer or ""
    records: list[LLMCallRecord] = []
    documents = documents_text(run)

    def call() -> dict[str, Any]:
        if isinstance(judge, JevClient):
            state = {"question": item.question, "target_variable": _target(item),
                     "diagnosis": item.diagnosis, "patient": item.patient,
                     "simulated_answer": answer, "retrieved_documents": documents}  # fmt: skip
            decision = judge.decide(state, JEV_QUESTIONS["faithfulness"], records)
            probability = float(decision["noul"])
            return {"probability": probability, "quote_ok": None,
                    "label": "supported" if probability >= 0.5 else "not_supported"}  # fmt: skip
        out: FaithfulnessOutput = judge._call(
            faithfulness_messages(item, run), FaithfulnessOutput, records
        )
        found = out.supported and quote_found(out.quote, documents)
        return out.model_dump() | {
            "quote_ok": found if out.supported else None,
            "label": "supported" if found else "not_supported",
        }

    base = _base(judge.model, item, run.config, answer, METRIC_RUBRIC)
    return _metric_record(base, "faithfulness", records, call)


def judge_alignment(
    judge: AnyJudge, item: Item, case: CaseStudy, run: RunRecord, rubric: str = "m2"
) -> MetricJudgment:
    answer = run.output_answer or ""
    records: list[LLMCallRecord] = []

    def call_levels() -> dict[str, Any]:
        if isinstance(judge, JevClient):
            decisions = judge.decide_all(
                _case_state(item, case, answer), JEV_LEVEL_QUESTIONS, records
            )
            expected, stated = (_jev_label(decisions[k]) for k in ("expected", "answer"))
            return {
                "expected": expected, "answer": stated, "quote_ok": None,
                "probabilities": {k: decisions[k].get("probabilities") for k in decisions},
                "label": alignment_label(expected, stated),
            }  # fmt: skip
        out: AlignmentLevelOutput = judge._call(
            _messages(ALIGNMENT_LEVEL_PROMPT, alignment_messages(item, case, answer)[1].content),
            AlignmentLevelOutput,
            records,
        )
        found = out.expected != "none" and quote_found(out.quote, _full_case(case))
        return out.model_dump() | {
            "quote_ok": None if out.expected == "none" else found,
            # An expectation that cannot be found in the case is not counted.
            "label": alignment_label(out.expected if found else "none", out.answer),
        }

    def call() -> dict[str, Any]:
        if rubric == "m2":
            return call_levels()
        if isinstance(judge, JevClient):
            decision = judge.decide(
                _case_state(item, case, answer), JEV_QUESTIONS["case_alignment"], records
            )
            return {
                "probabilities": decision.get("probabilities"),
                "confidence": decision.get("confidence"),
                "quote_ok": None,
                "label": _jev_label(decision),
            }
        out: AlignmentOutput = judge._call(
            alignment_messages(item, case, answer), AlignmentOutput, records
        )
        found = out.label != "neutral" and quote_found(out.quote, _full_case(case))
        return out.model_dump() | {
            "label_raw": out.label,
            "quote_ok": None if out.label == "neutral" else found,
            # A link to the case that cannot be found in the case is not counted.
            "label": out.label if found else "neutral",
        }

    base = _base(judge.model, item, run.config, answer, rubric)
    return _metric_record(base, "case_alignment", records, call)


def _case_state(item: Item, case: CaseStudy, answer: str) -> dict[str, str]:
    return {"question": item.question, "target_variable": _target(item),
            "diagnosis": case.diagnosis, "full_case_report": _full_case(case),
            "simulated_answer": answer}  # fmt: skip


def jev_existing_metric(
    jev: JevClient, item: Item, case: CaseStudy, run: RunRecord, metric: str
) -> MaskedCorrectnessJudgment | ConsistencyJudgment:
    """Masked correctness or factual consistency by the decision model, in the panel's format
    (its probabilities are kept in ``rationale``; it gives no range, value, or spans)."""
    answer = run.output_answer or ""
    records: list[LLMCallRecord] = []
    base = _base(jev.model, item, run.config, answer, RUBRIC)
    state = _case_state(item, case, answer)
    suffix = "_c" if item.question_set == "C" else ""
    try:
        if metric == "masked_correctness":
            state["true_value"] = _truth(item)
            decision = jev.decide(state, JEV_QUESTIONS[metric + suffix], records)
            return MaskedCorrectnessJudgment(
                **base, status="ok", llm_calls=records,
                output=MaskedCorrectnessOutput(
                    reference_range="", truth_category="not_applicable", answer_value="",
                    rationale=_jev_note(decision), verdict=_jev_label(decision),  # type: ignore[arg-type]
                ),
            )  # fmt: skip
        decision = jev.decide(state, JEV_QUESTIONS[metric + suffix], records)
        return ConsistencyJudgment(
            **base, status="ok", llm_calls=records,
            output=ConsistencyOutput(
                answer_value="", conflicting_facts=[], rationale=_jev_note(decision),
                verdict=_jev_label(decision),  # type: ignore[arg-type]
            ),
        )  # fmt: skip
    except MedSimError as exc:
        cls = MaskedCorrectnessJudgment if metric == "masked_correctness" else ConsistencyJudgment
        return cls(**base, status="error", error=str(exc)[:300], llm_calls=records)


# --- scoring (no API calls) ----------------------------------------------------------------------


@dataclass(frozen=True)
class Reference:
    """The panel's reading of one question: the median of the judges' numbers."""

    numeric: bool
    truth_low: float | None
    truth_high: float | None
    lower: float | None
    upper: float | None
    judges: int


def _panel_number(values: Sequence[float | None]) -> float | None:
    """Null when at least half of the judges give null, otherwise the median of the numbers."""
    given = [v for v in values if v is not None]
    return statistics.median(given) if len(given) * 2 > len(values) else None


def combine_reference(outputs: Sequence[ReferenceOutput]) -> Reference | None:
    if not outputs:
        return None
    numeric = sum(o.numeric for o in outputs) * 2 > len(outputs)
    return Reference(
        numeric=numeric,
        truth_low=_panel_number([o.truth_low for o in outputs]),
        truth_high=_panel_number([o.truth_high for o in outputs]),
        lower=_panel_number([o.reference_lower for o in outputs]),
        upper=_panel_number([o.reference_upper for o in outputs]),
        judges=len(outputs),
    )


def load_references(panel: Sequence[str], path: Path = REFERENCE_FILE) -> dict[str, Reference]:
    by_item: dict[str, dict[str, ReferenceOutput]] = {}
    for record in read_models(path, ReferenceJudgment):
        if (
            record.status == "ok"
            and record.output
            and record.judge_model in panel
            and record.rubric == METRIC_RUBRIC
        ):
            by_item.setdefault(record.item_id, {})[record.judge_model] = record.output
    combined = {k: combine_reference(list(v.values())) for k, v in by_item.items()}
    return {k: v for k, v in combined.items() if v is not None}


def value_score(reference: Reference, output: Mapping[str, Any], *, scaled: bool = False) -> float:
    """One judge's reading of one answer as a score: |z| capped; the cap if not comparable.
    ``scaled`` uses the revised scale (``zlog_score(scale_with_truth=True)``)."""
    low, high = output.get("answer_low"), output.get("answer_high")
    if not output.get("comparable") or low is None:
        return SCORE_CAP
    try:
        score = zlog_score_truth_range(
            reference.truth_low, reference.truth_high, float(low),
            None if high is None else float(high), lower=reference.lower, upper=reference.upper,
            scale_with_truth=scaled,
        )  # fmt: skip
    except (ValueError, ZeroDivisionError, OverflowError):
        return SCORE_CAP
    return SCORE_CAP if score is None else score.score


def scorable(reference: Reference | None) -> bool:
    """The zlog z-score applies: a numeric true value was read."""
    return bool(
        reference
        and reference.numeric
        and (reference.truth_low is not None or reference.truth_high is not None)
    )


def metric_path(ws: Workspace, metric: str) -> Path:
    return ws.root / "judge" / f"{metric}.jsonl"


def ok_metric_judgments(
    path: Path, judge_model: str, rubric: str = METRIC_RUBRIC
) -> dict[str, dict[str, Any]]:
    """Successful judgments by one model, by answer key (the latest wins)."""
    done: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(path):
        if (
            record.get("judge_model") == judge_model
            and record.get("rubric") == rubric
            and record.get("status") == "ok"
            and record.get("output") is not None
        ):
            done[record["answer_key"]] = record["output"]
    return done


# --- the step ------------------------------------------------------------------------------------

Job = tuple[str, Callable[[], BaseModel], JsonlWriter]


def eligible(metric: str, item: Item, run: RunRecord) -> bool:
    """Whether ``metric`` has a judge call for this answer (other answers score by rule)."""
    if not judgeable(run):
        return False
    if metric in SET_METRICS[item.question_set]:  # the two existing metrics (decision model)
        return metric != "masked_correctness" or item.truth is not None
    if item.question_set not in METRIC_SETS.get(metric, ()):
        return False
    if metric == "faithfulness":
        return run.config not in NO_DOCUMENT_CONFIGS and bool(run.documents)
    if metric == "zlog_value":
        return item.truth is not None
    return True


def plan_workspace(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[str],
    judges: Sequence[AnyJudge],
    metrics: Sequence[str],
    cases: Mapping[str, CaseStudy],
    references: Mapping[str, Reference],
    limit: int | None = None,
    alignment_rubric: str = "m2",
) -> dict[str, list[Job]]:
    """Jobs still to do in one workspace, by judge model."""
    by_id = {i.item_id: i for i in items}
    full = full_cases(items, cases)
    jobs: dict[str, list[Job]] = {j.model: [] for j in judges}
    runs = latest_runs(ws, configs)
    for metric in metrics:
        existing = metric in ("masked_correctness", "factual_consistency")
        path = (
            (ws.masked_correctness if metric == "masked_correctness" else ws.consistency)
            if existing
            else metric_path(ws, metric)
        )
        writer = JsonlWriter(path)
        for judge in judges:
            is_jev = isinstance(judge, JevClient)
            if existing != is_jev and existing:
                continue  # the chat judges do the existing metrics through `bench judge`
            if is_jev and metric == "zlog_value":
                continue  # a decision model cannot read out a number
            if existing:
                cls: Any = (
                    MaskedCorrectnessJudgment
                    if metric == "masked_correctness"
                    else ConsistencyJudgment
                )
                done: Mapping[str, Any] = ok_judgments(path, cls, judge.model)
            else:
                rubric = alignment_rubric if metric == "case_alignment" else METRIC_RUBRIC
                done = ok_metric_judgments(path, judge.model, rubric)
            planned = 0
            for per_item in runs.values():
                for item_id, run in per_item.items():
                    item = by_id.get(item_id)
                    if item is None or not eligible(metric, item, run):
                        continue
                    if metric == "zlog_value" and not scorable(references.get(item_id)):
                        continue
                    key = answer_key(item_id, run.config, run.output_answer or "")
                    if key in done or (limit is not None and planned >= limit):
                        continue
                    planned += 1
                    jobs[judge.model].append(
                        (
                            metric,
                            _job(judge, metric, item, full[item_id], run, alignment_rubric),
                            writer,
                        )
                    )
    return jobs


def _job(
    judge: AnyJudge,
    metric: str,
    item: Item,
    case: CaseStudy,
    run: RunRecord,
    alignment_rubric: str = "m2",
) -> Callable[[], BaseModel]:
    if metric in ("masked_correctness", "factual_consistency"):
        assert isinstance(judge, JevClient)
        return lambda: jev_existing_metric(judge, item, case, run, metric)
    if metric == "zlog_value":
        assert isinstance(judge, Judge)
        return lambda: judge_value(judge, item, run)
    if metric == "faithfulness":
        return lambda: judge_faithfulness(judge, item, run)
    return lambda: judge_alignment(judge, item, case, run, alignment_rubric)


def plan_reference(
    items: Sequence[Item], judges: Sequence[Judge], limit: int | None = None
) -> dict[str, list[Job]]:
    writer = JsonlWriter(REFERENCE_FILE)
    done = {(r.item_id, r.judge_model) for r in read_models(REFERENCE_FILE, ReferenceJudgment)
            if r.status == "ok" and r.rubric == METRIC_RUBRIC}  # fmt: skip
    jobs: dict[str, list[Job]] = {j.model: [] for j in judges}
    for judge in judges:
        todo = [i for i in items if i.truth is not None and (i.item_id, judge.model) not in done]
        for item in todo[:limit]:
            jobs[judge.model].append(("reference", _reference_job(judge, item), writer))
    return jobs


def _reference_job(judge: Judge, item: Item) -> Callable[[], BaseModel]:
    return lambda: judge_reference(judge, item)


def run_jobs(jobs: Mapping[str, Sequence[Job]], workers: int) -> dict[str, Any]:
    """Every judge works through its own jobs in its own pool, so a slow or rate-limited judge
    does not hold back the others. Stops submitting when the account runs out of credit."""
    counts: Counter[str] = Counter()
    costs: dict[str, float] = {}
    out_of_credit = threading.Event()

    def guarded(fn: Callable[[], BaseModel]) -> BaseModel | None:
        return None if out_of_credit.is_set() else fn()

    pools = {model: ThreadPoolExecutor(max_workers=max(1, workers)) for model in jobs}
    futures: dict[Future[BaseModel | None], tuple[str, str, JsonlWriter]] = {}
    for model, model_jobs in jobs.items():
        for metric, fn, writer in model_jobs:
            futures[pools[model].submit(guarded, fn)] = (model, metric, writer)
    total = Counter((model, metric) for model, metric, _ in futures.values())
    finished: Counter[tuple[str, str]] = Counter()
    try:
        for future in as_completed(futures):
            model, metric, writer = futures[future]
            record = future.result()
            if record is None:
                counts[f"{metric} [{model}]:skipped"] += 1
                continue
            writer.write(record)
            status = getattr(record, "status", "ok")
            counts[f"{metric} [{model}]:{status}"] += 1
            label = f"{metric} [{model}]"
            costs[label] = costs.get(label, 0.0) + calls_cost(getattr(record, "llm_calls", []))
            if status == "error" and "402" in (getattr(record, "error", "") or ""):
                if not out_of_credit.is_set():
                    logger.error("HTTP 402 (out of credit): no further jobs are started")
                out_of_credit.set()
            finished[(model, metric)] += 1
            n, of = finished[(model, metric)], total[(model, metric)]
            if n % 200 == 0 or n == of:
                logger.info("%s: %d/%d ($%.3f)", label, n, of, costs[label])
    finally:
        for pool in pools.values():
            pool.shutdown(wait=True)
    return {"counts": dict(sorted(counts.items())),
            "cost_usd": {k: round(v, 4) for k, v in sorted(costs.items())},
            "total_cost_usd": round(sum(costs.values()), 4),
            "out_of_credit": out_of_credit.is_set()}  # fmt: skip


def run_workspaces(
    index: Mapping[str, Any], runs: Sequence[int]
) -> list[tuple[int, str, Workspace]]:
    found = []
    for run in runs:
        paths = index["runs"][str(run)]
        for kind, key in (("ab", "sets_ab"), ("c", "set_c")):
            found.append((run, kind, Workspace(REPO / paths[key])))
    return found


def parse_runs(text: str) -> list[int]:
    runs: list[int] = []
    for part in text.split(","):
        first, _, last = part.partition("-")
        runs.extend(range(int(first), int(last or first) + 1))
    return runs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bench.answer_metrics", description=__doc__)
    parser.add_argument(
        "--runs", default="1-10", help='Runs of the repeat index, e.g. "2" or "1-10".'
    )
    parser.add_argument("--metrics", required=True,
                        help="Comma-separated: reference, zlog_value, faithfulness, "
                        "case_alignment, masked_correctness, factual_consistency (the last two "
                        "only for the decision model).")  # fmt: skip
    parser.add_argument("--judges", help="Comma-separated judge models; default: the panel.")
    parser.add_argument("--kinds", default="ab,c")
    parser.add_argument("--alignment-rubric", default="m2", choices=["m1", "m2"],
                        help="m1: one verdict; m2: expected against stated level.")  # fmt: skip
    parser.add_argument("--configs", help="Default: every configuration that has run results.")
    parser.add_argument("--workers", type=int, default=24, help="Parallel calls per judge.")
    parser.add_argument(
        "--limit", type=int, help="At most this many answers per metric, judge and workspace."
    )
    parser.add_argument(
        "--cases", type=Path, default=REPO / "cases/combined_272_whole_chunking.json"
    )
    args = parser.parse_args(argv)

    settings, bench = load_settings(), BenchSettings()
    SHARED.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    log_path = SHARED / "logs" / f"{stamp}_{args.metrics.replace(',', '+')}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger("bench").setLevel(logging.INFO)
    logger.info("answer_metrics %s", " ".join(sys.argv[1:] if argv is None else argv))

    models = args.judges.split(",") if args.judges else list(bench.judge_models)
    metrics = args.metrics.split(",")
    chat_models = [m for m in models if m != JEV_MODEL]
    index = json.loads((RESULTS / "repeats" / "index.json").read_text(encoding="utf-8"))
    cases = load_cases(args.cases)
    llm = OpenRouterClient(settings)
    if chat_models:
        llm.verify_models(chat_models)
    jev = JevClient(settings) if JEV_MODEL in models else None
    judges: list[AnyJudge] = [
        Judge(llm, m, bench.judge_max_tokens, max_attempts=bench.judge_max_attempts,
              backoff_s=bench.judge_retry_backoff_s)
        for m in chat_models
    ]  # fmt: skip
    if jev:
        judges.append(jev)

    jobs: dict[str, list[Job]] = {j.model: [] for j in judges}
    workspaces = [
        w for w in run_workspaces(index, parse_runs(args.runs)) if w[1] in args.kinds.split(",")
    ]
    if "reference" in metrics:
        seen: dict[str, Item] = {}
        for _, _, ws in run_workspaces(index, [1]):
            seen.update({i.item_id: i for i in read_models(ws.items, Item)})
        chat = [j for j in judges if isinstance(j, Judge)]
        for model, planned in plan_reference(list(seen.values()), chat, args.limit).items():
            jobs[model] += planned
    answer_metrics = [m for m in metrics if m != "reference"]
    if answer_metrics:
        references = load_references(chat_models or list(bench.judge_models))
        for _, _, ws in workspaces:
            configs = args.configs.split(",") if args.configs else ws.run_configs()
            configs = [c for c in configs if ws.run_file(c).exists()]
            planned_ws = plan_workspace(
                ws, read_models(ws.items, Item), configs, judges, answer_metrics, cases,
                references, args.limit, args.alignment_rubric,
            )  # fmt: skip
            for model, planned in planned_ws.items():
                jobs[model] += planned
    logger.info("planned: %s", {m: len(j) for m, j in jobs.items()})
    summary = run_jobs(jobs, args.workers)
    llm.close()
    if jev:
        jev.close()
    summary["planned"] = {m: len(j) for m, j in jobs.items()}
    logger.info("summary: %s", json.dumps(summary))
    print(json.dumps(summary, indent=1))
    return 1 if summary["out_of_credit"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
