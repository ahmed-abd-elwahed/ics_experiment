"""Step 1: list each case's measured values, and keep the ones usable as hidden test values."""

from __future__ import annotations

import logging
import random
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from bench.schemas import (
    ELIGIBLE_CATEGORIES,
    CaseFacts,
    CheckedFact,
    ExtractedFact,
    ExtractorOutput,
)
from bench.text import HAS_MEASUREMENT, case_text, contains_verbatim, count_value, normalize
from bench.workspace import JsonlWriter, Workspace, read_models
from medsim.errors import MedSimError
from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import CaseStudy, ChatMessage, LLMCallRecord

logger = logging.getLogger("bench.extract")

SYSTEM_PROMPT = """\
You extract measured patient values from a published case report. They will be hidden from a \
patient simulator and used as ground truth, so precision matters more than recall.

List every numeric measurement of THIS patient stated in the CASE TEXT: vital signs, laboratory \
results, body measurements (weight, height, BMI), and also imaging sizes, scores, and doses (so \
they can be excluded).

For each value:
- variable: the standard clinical name, specific enough to ask about ("serum creatinine", \
"heart rate", "hemoglobin", "blood pressure").
- value: the number exactly as written, without the unit ("2.4", "100/60", "15,200").
- unit: the unit exactly as written, or null.
- timepoint: when it was measured, as a short phrase starting with a preposition ("at \
presentation", "on day 3", "at discharge"), or null if the text does not say.
- span: the shortest verbatim excerpt of the CASE TEXT that contains the value. Copy it \
exactly, character for character.
- category: vital_sign | laboratory | anthropometric | imaging_measurement | score_or_scale | \
medication_or_dose | other.
- askable_without_diagnosis: true if a clinician who does not know the diagnosis would \
plausibly ask for this measurement (routine vitals and labs: true; the size of a specific \
lesion or a test named after the disease: false).
- characteristic_of_diagnosis: true if this variable is typically abnormal in the DIAGNOSIS.

Rules: one entry per value and timepoint; a blood pressure is one entry ("120/80"); never infer \
values that are not written; skip ages, dates, durations, and counts of events. \
Return only a JSON object with key "facts"."""


def build_messages(case: CaseStudy) -> list[ChatMessage]:
    user = f"DIAGNOSIS: {case.diagnosis}\n\nCASE TEXT:\n{case_text(case)}"
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=user),
    ]


def check_facts(facts: Sequence[ExtractedFact], text: str) -> list[CheckedFact]:
    """Keep facts whose span and value are verbatim, of an askable kind, and not repeated."""
    per_variable = Counter(
        normalize(f.variable) for f in facts if f.category in ELIGIBLE_CATEGORIES
    )
    checked: list[CheckedFact] = []
    for fact in facts:
        reason: str | None = None
        if not any(ch.isdigit() for ch in fact.value):
            reason = "no_number"
        elif not contains_verbatim(text, fact.span):
            reason = "span_not_verbatim"
        elif count_value(fact.span, fact.value) == 0:
            reason = "value_not_in_span"
        elif fact.category not in ELIGIBLE_CATEGORIES:
            reason = f"category:{fact.category}"
        elif not fact.askable_without_diagnosis:
            reason = "not_askable_without_diagnosis"
        elif per_variable[normalize(fact.variable)] > 1:
            reason = "variable_reported_more_than_once"
        checked.append(
            CheckedFact(**fact.model_dump(), eligible=reason is None, reject_reason=reason)
        )
    return checked


def extract_case(case: CaseStudy, *, llm: LLMClient, model: str, max_tokens: int) -> CaseFacts:
    records: list[LLMCallRecord] = []
    try:
        output = call_structured(
            llm, stage="extractor", messages=build_messages(case), output_model=ExtractorOutput,
            temperature=0.0, max_tokens=max_tokens, model=model, records=records,
        )  # fmt: skip
    except MedSimError as exc:
        return CaseFacts(
            case_id=case.case_id, diagnosis=case.diagnosis, status="error",
            error=str(exc)[:500], llm_calls=records,
        )  # fmt: skip
    return CaseFacts(
        case_id=case.case_id,
        diagnosis=case.diagnosis,
        facts=check_facts(output.facts, case_text(case)),
        llm_calls=records,
    )


def select_cases(cases: dict[str, CaseStudy], *, limit: int | None, seed: int) -> list[str]:
    """Cases that mention at least one measurement, in a seeded random order."""
    ids = sorted(cid for cid, case in cases.items() if HAS_MEASUREMENT.search(case_text(case)))
    random.Random(seed).shuffle(ids)
    return ids if limit is None else ids[:limit]


def run_extract(
    ws: Workspace,
    cases: dict[str, CaseStudy],
    case_ids: Sequence[str],
    *,
    llm: LLMClient,
    model: str,
    max_tokens: int,
    workers: int = 4,
) -> dict[str, int]:
    done = {f.case_id for f in read_models(ws.facts, CaseFacts) if f.status == "ok"}
    todo = [cid for cid in case_ids if cid not in done]
    writer = JsonlWriter(ws.facts)
    counts: Counter[str] = Counter()

    def work(case_id: str) -> CaseFacts:
        return extract_case(cases[case_id], llm=llm, model=model, max_tokens=max_tokens)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for result in pool.map(work, todo):
            writer.write(result)
            counts[result.status] += 1
            eligible = sum(f.eligible for f in result.facts)
            counts["eligible_facts"] += eligible
            logger.info(
                "extract %s: %s, %d facts, %d eligible",
                result.case_id, result.status, len(result.facts), eligible,
            )  # fmt: skip
    return {"requested": len(case_ids), "already_done": len(done & set(case_ids)), **counts}
