"""Step 4: LLM judge.

Pass 1 (never sees the true value) records facets for one document at a time; code turns them
into relevance (0-3) and usefulness (0-2), and a verbatim-quote check guards against invented
evidence. Pass 2 (set A only, documents with usefulness >= 1) compares the document's evidence
with the hidden true value: correctness 0-2. The answer check grades Stage C's final value.
Documents retrieved by several configurations for the same question are judged once.
"""

from __future__ import annotations

import hashlib
import logging
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import partial
from typing import Any

from bench.schemas import (
    AnswerJudgment,
    AnswerOutput,
    DocRecord,
    Item,
    Pass1Judgment,
    Pass1Output,
    Pass2Judgment,
    Pass2Output,
    RunRecord,
    calls_cost,
)
from bench.text import quote_found
from bench.workspace import JsonlWriter, Workspace, latest_by, read_models
from medsim.errors import MedSimError
from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import ChatMessage, LLMCallRecord

logger = logging.getLogger("bench.judge")

RUBRIC = "v1"

PASS1_PROMPT = """\
You grade ONE retrieved biomedical document for a patient simulator. The simulator's record \
lacks a value for the TARGET VARIABLE; it retrieved literature to estimate a plausible value for \
this PATIENT. Grade only what the DOCUMENT text itself says; never fill gaps with your own \
knowledge.

Fields:
- rationale: one or two sentences on how the document relates to the target and patient.
- evidence_quote: the shortest verbatim span of the DOCUMENT (at most ~300 characters) that \
carries the evidence about the target variable, copied exactly; "" if there is none.
- evidence_value: the value, range, or frequency with its unit, exactly as the document gives \
it; "" if none.
- evidence_population: who that evidence describes (e.g. "42 adults with severe TR"); "" if none.
- variable_match: "exact" = the document reports the same measurement as the TARGET VARIABLE \
(synonyms, abbreviations, and named abnormalities of it count, e.g. "hyperbilirubinemia" for \
serum bilirubin); "related" = a different but physiologically linked measurement (e.g. \
creatinine clearance for serum creatinine); "absent" = neither.
- condition_match: "exact" = the patient's DIAGNOSIS or a synonym; "related" = a condition \
sharing its mechanism, organ-level syndrome, parent category, or a direct complication; \
"unrelated" = anything else, including healthy or general populations.
- population_match: "match" = humans comparable to the PATIENT (age group, sex where relevant, \
setting); patients with the condition and no further detail count as "match"; "partial" = \
humans differing in a way that may shift the value (other age band, severity, setting); \
"unstated" = no population described at all; "mismatch" = animals, in-vitro work, or a clearly \
incompatible population (e.g. neonates for an adult).
- evidence_type: "quantitative" = a value, range, mean±SD, median/IQR, cut-off, or % of \
patients abnormal for the TARGET VARIABLE; "qualitative" = only a direction or presence \
("elevated", "usually normal"); "none".
Return only a JSON object with exactly these keys."""

PASS2_PROMPT = """\
You compare literature evidence with a patient's TRUE value, which was hidden from a patient \
simulator. Decide whether the DOCUMENT's evidence points to the TRUE value.

Fields:
- reference_range: the usual reference range you use for this variable in this kind of patient, \
with unit.
- truth_category: the TRUE value relative to that range: "low", "normal", or "high" (for blood \
pressure, use the more abnormal component).
- document_prediction: what the document implies this patient's value would be (a range or a \
direction), in one short phrase.
- rationale: one or two sentences.
- verdict: "within" = the TRUE value lies inside the range the document reports for a \
comparable population (a stated range, mean ± 2 SD, or IQR); "direction" = outside that range \
but in the same category (low/normal/high) the document implies, or the document gives only a \
direction and it matches; "contradicts" = the document implies a different category than the \
TRUE value; "not_comparable" = the evidence cannot be compared with the TRUE value (another \
variable, units that cannot be converted, or no value for this variable).
Convert units when needed. Return only a JSON object with exactly these keys."""

ANSWER_PROMPT = """\
A patient simulator did not know a patient's TRUE value and synthesized one from literature. \
Compare the SIMULATED ANSWER with the TRUE value.

Fields:
- reference_range: the usual reference range for this variable in this kind of patient, with \
unit.
- truth_category: the TRUE value relative to that range: "low", "normal", or "high".
- answer_value: the value the simulated answer states, with unit ("" if none).
- rationale: one or two sentences.
- verdict: "close" = clinically the same finding (same category and within about 10-15% or the \
measurement's usual variability); "same_category" = same low/normal/high category but not close; \
"different_category"; "not_comparable" = no value, or a different variable.
Convert units when needed. Return only a JSON object with exactly these keys."""


# --- grading ------------------------------------------------------------------------------------


def relevance_grade(out: Pass1Output) -> int:
    """3: exact variable, exact condition, matching population. 2: exact variable with a related
    condition or a partly matching population. 1: only the variable or only the condition.
    0: neither, or a mismatched population (animals, in vitro)."""
    if out.population_match == "mismatch":
        return 0
    v, c = out.variable_match, out.condition_match
    if v == "exact" and c == "exact" and out.population_match == "match":
        return 3
    if v == "exact" and c in ("exact", "related"):
        return 2
    if (v == "exact") or (v == "related" and c != "unrelated") or (v == "absent" and c == "exact"):
        return 1
    return 0


def usefulness_grade(out: Pass1Output, quote_ok: bool) -> int:
    """2: a number for the exact variable in the exact or a related condition. 1: a number from
    a population without the condition (e.g. a reference range) or for a related variable, or a
    direction in the right condition. 0: nothing usable, a mismatched population, or a quote
    that is not in the document."""
    if out.evidence_type == "none" or out.variable_match == "absent":
        return 0
    if out.population_match == "mismatch" or not quote_ok:
        return 0
    on_condition = out.condition_match in ("exact", "related")
    if out.evidence_type == "quantitative":
        if out.variable_match == "exact" and on_condition:
            return 2
        return 1
    return 1 if on_condition else 0


CORRECTNESS = {"within": 2, "direction": 1, "contradicts": 0}


def correctness_grade(out: Pass2Output) -> int | None:
    return CORRECTNESS.get(out.verdict)


# --- prompts ------------------------------------------------------------------------------------


def _target(item: Item) -> str:
    when = f" ({item.timepoint})" if item.timepoint else ""
    return f"{item.variable}{when}"


def _truth(item: Item, override: str | None = None) -> str:
    assert item.truth is not None
    if override is not None:
        return override
    unit = f" {item.truth.unit}" if item.truth.unit else ""
    return f'{item.truth.value}{unit} (case report: "{item.truth.span}")'


def _document(title: str | None, text: str) -> str:
    return f"Title: {title or '(none)'}\nText: {text}"


def pass1_messages(item: Item, title: str | None, text: str) -> list[ChatMessage]:
    user = (
        f"TARGET VARIABLE: {_target(item)}\nDIAGNOSIS: {item.diagnosis}\n"
        f"PATIENT: {item.patient}\n\nDOCUMENT:\n{_document(title, text)}"
    )
    return [
        ChatMessage(role="system", content=PASS1_PROMPT),
        ChatMessage(role="user", content=user),
    ]


def pass2_messages(
    item: Item, title: str | None, text: str, evidence: Pass1Output, truth: str | None = None
) -> list[ChatMessage]:
    user = (
        f"TARGET VARIABLE: {_target(item)}\nDIAGNOSIS: {item.diagnosis}\n"
        f"PATIENT: {item.patient}\nTRUE VALUE: {_truth(item, truth)}\n\n"
        f"EVIDENCE FOUND IN THE DOCUMENT:\n- quote: {evidence.evidence_quote}\n"
        f"- value: {evidence.evidence_value}\n- population: {evidence.evidence_population}\n\n"
        f"DOCUMENT:\n{_document(title, text)}"
    )
    return [
        ChatMessage(role="system", content=PASS2_PROMPT),
        ChatMessage(role="user", content=user),
    ]


def answer_messages(item: Item, answer: str) -> list[ChatMessage]:
    user = (
        f"TARGET VARIABLE: {_target(item)}\nDIAGNOSIS: {item.diagnosis}\n"
        f"PATIENT: {item.patient}\nTRUE VALUE: {_truth(item)}\n\nSIMULATED ANSWER: {answer}"
    )
    return [
        ChatMessage(role="system", content=ANSWER_PROMPT),
        ChatMessage(role="user", content=user),
    ]


# --- judge calls --------------------------------------------------------------------------------


def doc_key(item_id: str, doc_id: str, text: str) -> str:
    blob = f"{item_id}\x1f{doc_id}\x1f{text}".encode()
    return hashlib.sha256(blob).hexdigest()[:20]


def answer_key(item_id: str, config: str, answer: str) -> str:
    return hashlib.sha256(f"{item_id}\x1f{config}\x1f{answer}".encode()).hexdigest()[:20]


@dataclass
class Judge:
    llm: LLMClient
    model: str
    max_tokens: int

    def _call(
        self, messages: list[ChatMessage], output: type[Any], records: list[LLMCallRecord]
    ) -> Any:
        return call_structured(
            self.llm, stage="judge", messages=messages, output_model=output, temperature=0.0,
            max_tokens=self.max_tokens, model=self.model, records=records,
        )  # fmt: skip

    def _doc_fields(self, item: Item, doc: DocRecord) -> dict[str, Any]:
        return {
            "doc_key": doc_key(item.item_id, doc.doc_id, doc.text),
            "item_id": item.item_id,
            "doc_id": doc.doc_id,
            "source": doc.source,
            "judge_model": self.model,
            "rubric": RUBRIC,
        }

    def pass1(self, item: Item, doc: DocRecord, *, text: str | None = None) -> Pass1Judgment:
        text = doc.text if text is None else text
        records: list[LLMCallRecord] = []
        base = self._doc_fields(item, doc)
        try:
            out: Pass1Output = self._call(
                pass1_messages(item, doc.title, text), Pass1Output, records
            )
        except MedSimError as exc:
            return Pass1Judgment(**base, status="error", error=str(exc)[:300], llm_calls=records)
        ok = out.evidence_type == "none" or quote_found(
            out.evidence_quote, f"{doc.title or ''} {text}"
        )
        return Pass1Judgment(
            **base, status="ok", output=out, quote_ok=ok, relevance=relevance_grade(out),
            usefulness=usefulness_grade(out, ok), llm_calls=records,
        )  # fmt: skip

    def pass2(
        self, item: Item, doc: DocRecord, evidence: Pass1Output, *, truth: str | None = None
    ) -> Pass2Judgment:
        records: list[LLMCallRecord] = []
        base = self._doc_fields(item, doc) | {"truth_override": truth}
        try:
            out: Pass2Output = self._call(
                pass2_messages(item, doc.title, doc.text, evidence, truth), Pass2Output, records
            )
        except MedSimError as exc:
            return Pass2Judgment(**base, status="error", error=str(exc)[:300], llm_calls=records)
        return Pass2Judgment(
            **base, status="ok", output=out, correctness=correctness_grade(out), llm_calls=records
        )

    def answer(self, item: Item, run: RunRecord) -> AnswerJudgment:
        records: list[LLMCallRecord] = []
        answer = run.output_answer or ""
        base: dict[str, Any] = {"item_id": item.item_id, "config": run.config,
                "answer_key": answer_key(item.item_id, run.config, answer),
                "judge_model": self.model, "rubric": RUBRIC}  # fmt: skip
        try:
            out: AnswerOutput = self._call(answer_messages(item, answer), AnswerOutput, records)
        except MedSimError as exc:
            return AnswerJudgment(**base, status="error", error=str(exc)[:300], llm_calls=records)
        return AnswerJudgment(**base, status="ok", output=out, llm_calls=records)


# --- step ---------------------------------------------------------------------------------------


def latest_runs(ws: Workspace, configs: Iterable[str]) -> dict[str, dict[str, RunRecord]]:
    """Latest successful run record per item, per configuration."""
    runs: dict[str, dict[str, RunRecord]] = {}
    for config in configs:
        latest = latest_by(read_models(ws.run_file(config), RunRecord), lambda r: r.item_id)
        runs[config] = {k: r for k, r in latest.items() if r.status == "ok"}
    return runs


def ok_judgments(path: Any, model_cls: type[Any], judge_model: str) -> dict[str, Any]:
    records = [r for r in read_models(path, model_cls) if r.judge_model == judge_model]
    records = [
        r for r in records if r.rubric == RUBRIC and getattr(r, "truth_override", None) is None
    ]
    key = "answer_key" if model_cls is AnswerJudgment else "doc_key"
    return {getattr(k, key): k for k in records if k.status == "ok"}


def run_judge(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[str],
    judge: Judge,
    *,
    workers: int = 8,
) -> dict[str, Any]:
    """Pass 1 and the answer check run together (they are independent); pass 2 follows,
    because it needs pass 1's usefulness grades."""
    by_id = {i.item_id: i for i in items}
    runs = latest_runs(ws, configs)

    # Pass 1: unique documents per question, pooled across configurations.
    docs: dict[str, tuple[Item, DocRecord]] = {}
    for per_item in runs.values():
        for item_id, run in per_item.items():
            if item_id in by_id:
                for doc in run.documents:
                    docs.setdefault(doc_key(item_id, doc.doc_id, doc.text), (by_id[item_id], doc))
    done1 = ok_judgments(ws.pass1, Pass1Judgment, judge.model)
    todo1 = [pair for key, pair in docs.items() if key not in done1]

    # Answer check: set A questions that got a literature answer.
    done3 = ok_judgments(ws.answers, AnswerJudgment, judge.model)
    todo3 = [
        (by_id[item_id], run)
        for per_item in runs.values()
        for item_id, run in per_item.items()
        if item_id in by_id
        and by_id[item_id].truth is not None
        and run.answer_source == "literature"
        and answer_key(item_id, run.config, run.output_answer or "") not in done3
    ]
    counts: Counter[str] = Counter()
    costs: dict[str, float] = {}
    pass1_writer, answer_writer = JsonlWriter(ws.pass1), JsonlWriter(ws.answers)
    _run_parallel(
        [("pass1", partial(judge.pass1, *pair), pass1_writer) for pair in todo1]
        + [("answer", partial(judge.answer, *pair), answer_writer) for pair in todo3],
        counts, costs, workers,
    )  # fmt: skip

    # Pass 2: set A documents with usefulness >= 1.
    done1 = ok_judgments(ws.pass1, Pass1Judgment, judge.model)
    done2 = ok_judgments(ws.pass2, Pass2Judgment, judge.model)
    todo2 = []
    for key, (item, doc) in docs.items():
        judged = done1.get(key)
        if item.truth is None or judged is None or key in done2:
            continue
        if (judged.usefulness or 0) >= 1 and judged.output is not None:
            todo2.append((item, doc, judged.output))
    pass2_writer = JsonlWriter(ws.pass2)
    _run_parallel(
        [("pass2", partial(judge.pass2, *triple), pass2_writer) for triple in todo2],
        counts, costs, workers,
    )  # fmt: skip
    return {"documents": len(docs), "pass1_todo": len(todo1), "pass2_todo": len(todo2),
            "answer_todo": len(todo3), **counts,
            "cost_usd": {k: round(v, 4) for k, v in costs.items()}}  # fmt: skip


def _run_parallel(
    jobs: Sequence[tuple[str, Callable[[], Any], JsonlWriter]],
    counts: Counter[str],
    costs: dict[str, float],
    workers: int,
) -> None:
    """Run labelled jobs in one pool; write each record as it finishes."""
    total: Counter[str] = Counter(label for label, _, _ in jobs)
    finished: Counter[str] = Counter()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(fn): (label, writer) for label, fn, writer in jobs}
        for future in as_completed(futures):
            label, writer = futures[future]
            record = future.result()
            writer.write(record)
            counts[f"{label}:{record.status}"] += 1
            costs[label] = costs.get(label, 0.0) + calls_cost(record.llm_calls)
            finished[label] += 1
            if finished[label] % 25 == 0 or finished[label] == total[label]:
                logger.info("judge %s: %d/%d", label, finished[label], total[label])
