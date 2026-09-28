"""Set C: questions about information the case states, written by an LLM.

The environment sees the whole case, so it can answer a set C question from the case text itself
without retrieval. One question per case. The writer LLM returns the question with its answer and
the verbatim span of the case that states it; code keeps a question only if the span is verbatim
in the case, a numeric answer occurs in its span, and the question neither names the diagnosis
nor gives away the answer. A rejected question is rewritten once with the reason; a case whose
second question also fails is recorded as rejected.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bench.schemas import Item, RejectedItem, SetCQuestionOutput, Truth
from bench.text import case_text, count_value, patient_summary, quote_found
from bench.workspace import JsonlWriter, Workspace, read_models
from medsim.errors import MedSimError
from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import CaseStudy, ChatMessage, LLMCallRecord

logger = logging.getLogger("bench.set_c")

SET_C_FORMAT = "ics-bench-set-c-questions"

SET_C_PROMPT = """\
You write one benchmark question about a published case report. A patient simulator will be \
given this CASE TEXT and asked the question, so the question must be answerable from the case \
text alone.

Pick one fact about THIS patient that the CASE TEXT states explicitly and that a clinician who \
does not know the diagnosis could plausibly ask about: preferably a measured value (a vital \
sign, laboratory result, or body measurement), otherwise a specific examination, imaging, or \
history finding. Never pick the diagnosis, a differential diagnosis, or anything that names or \
strongly hints at the DIAGNOSIS; do not pick treatments or outcomes.

Fields:
- question: one short question, e.g. "What was the patient's serum sodium on admission?" or \
"Did the patient have a heart murmur on examination?". It must not contain the answer or the \
diagnosis.
- variable: the clinical variable or finding asked about ("serum sodium", "heart murmur").
- answer: the answer as the case states it, as short as possible ("132", "present, grade 3/6 \
systolic").
- unit: the unit of a numeric answer exactly as written, or null.
- timepoint: when it applies, as a short phrase ("on admission"), or null.
- span: the shortest verbatim excerpt of the CASE TEXT that states the answer. Copy it exactly, \
character for character.
- answer_type: "numeric" | "finding" | "history".
- category: vital_sign | laboratory | anthropometric | examination | imaging | history | other.
Return only a JSON object with exactly these keys."""

RETRY_NOTE = "Your previous question was rejected: {reason}. Write a new question that avoids this."


def check_question(out: SetCQuestionOutput, case: CaseStudy) -> str | None:
    """Why the question cannot be used, or None."""
    text = case_text(case)
    if not out.question.strip() or not out.answer.strip():
        return "empty question or answer"
    if not quote_found(out.span, text):
        return "the span is not verbatim in the case"
    if case.diagnosis.strip() and case.diagnosis.casefold() in out.question.casefold():
        return "the question names the diagnosis"
    if out.answer_type == "numeric":
        if not count_value(out.span, out.answer):
            return "the numeric answer does not occur in its span"
        if count_value(out.question, out.answer):
            return "the question contains the answer"
    return None


class SetCWriter:
    def __init__(self, llm: LLMClient, *, model: str, max_tokens: int) -> None:
        self.llm = llm
        self.model = model
        self.max_tokens = max_tokens

    def _ask(self, case: CaseStudy, records: list[LLMCallRecord], note: str | None) -> Any:
        user = f"DIAGNOSIS: {case.diagnosis}\n\nCASE TEXT:\n{case_text(case)}"
        messages = [ChatMessage(role="system", content=SET_C_PROMPT),
                    ChatMessage(role="user", content=user)]  # fmt: skip
        if note:
            messages.append(ChatMessage(role="user", content=note))
        return call_structured(
            self.llm, stage="question_writer", messages=messages, output_model=SetCQuestionOutput,
            temperature=0.0, max_tokens=self.max_tokens, model=self.model, records=records,
        )  # fmt: skip

    def build(self, case: CaseStudy) -> Item | RejectedItem:
        records: list[LLMCallRecord] = []
        item_id = f"C:{case.case_id}"
        reason: str | None = None
        out: SetCQuestionOutput | None = None
        for attempt in range(2):
            note = RETRY_NOTE.format(reason=reason) if attempt and reason else None
            try:
                out = self._ask(case, records, note)
            except MedSimError as exc:
                error = {"error": str(exc)[:300]}
                return RejectedItem(item_id=item_id, question_set="C", case_id=case.case_id,
                                    variable="", reason="llm_error", detail=error,
                                    llm_calls=records)  # fmt: skip
            reason = check_question(out, case)
            if reason is None:
                break
        assert out is not None
        if reason is not None:
            return RejectedItem(item_id=item_id, question_set="C", case_id=case.case_id,
                                variable=out.variable, reason=reason,
                                detail=out.model_dump(mode="json"), llm_calls=records)  # fmt: skip
        return Item(
            item_id=item_id, question_set="C", case_id=case.case_id, diagnosis=case.diagnosis,
            question=out.question.strip(), variable=out.variable, category=out.category,
            timepoint=out.timepoint,
            truth=Truth(value=out.answer.strip(), unit=out.unit, span=out.span),
            case=case, patient=patient_summary(case), llm_calls=records,
        )  # fmt: skip


def run_set_c(
    ws: Workspace,
    cases: Mapping[str, CaseStudy],
    writer: SetCWriter,
    *,
    workers: int = 8,
) -> dict[str, Any]:
    """One set C question per case, written in parallel; resumes, retrying LLM errors."""
    accepted = {i.case_id for i in read_models(ws.items, Item) if i.question_set == "C"}
    final = {
        r.case_id
        for r in read_models(ws.rejected, RejectedItem)
        if r.question_set == "C" and r.reason != "llm_error"
    }
    todo = [c for cid, c in cases.items() if cid not in accepted and cid not in final]
    items, rejected = JsonlWriter(ws.items), JsonlWriter(ws.rejected)
    counts = {"accepted": 0, "rejected": 0}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for n, result in enumerate(pool.map(writer.build, todo), 1):
            if isinstance(result, Item):
                items.write(result)
                counts["accepted"] += 1
            else:
                rejected.write(result)
                counts["rejected"] += 1
                counts[f"rejected:{result.reason}"] = counts.get(f"rejected:{result.reason}", 0) + 1
            if n % 25 == 0 or n == len(todo):
                logger.info("set C: %d/%d cases", n, len(todo))
    total = sum(1 for i in read_models(ws.items, Item) if i.question_set == "C")
    return {"cases": len(cases), "todo": len(todo), **counts, "total_accepted": total}


def export_set_c(ws: Workspace, *, cases_file: Path, out_file: Path, model: str) -> dict[str, Any]:
    """The workspace's set C questions as a reusable file, with how they were made."""
    items = [i for i in read_models(ws.items, Item) if i.question_set == "C"]
    rejected = [r for r in read_models(ws.rejected, RejectedItem) if r.question_set == "C"]
    calls = [c for i in items for c in i.llm_calls] + [c for r in rejected for c in r.llm_calls]
    counts = {"accepted": len(items), "rejected": len(rejected)}
    data: dict[str, Any] = {
        "format": SET_C_FORMAT,
        "version": 1,
        "metadata": {
            "title": "Benchmark set C: one question per case about information the case states",
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "source_dataset": {
                "path": str(cases_file),
                "sha256": hashlib.sha256(cases_file.read_bytes()).hexdigest(),
            },
            "writer_model": model,
            "prompt": SET_C_PROMPT,
            "retry_note": RETRY_NOTE,
            "checks": [
                "the span is verbatim in the case",
                "a numeric answer occurs in its span",
                "the question does not name the diagnosis",
                "a numeric answer does not occur in the question",
            ],
            "counts": counts,
            "cost_usd": round(sum(c.cost_usd or 0.0 for c in calls), 6),
        },
        "items": [i.model_dump(mode="json", exclude={"llm_calls"}) for i in items],
        "rejected": [r.model_dump(mode="json", exclude={"llm_calls"}) for r in rejected],
    }
    out_file.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"file": str(out_file), **counts}
