"""Step 2 ("redact"): build the question sets.

Set A hides one value the case reports: an LLM removes it, deterministic checks confirm it is
gone and nothing else changed, and medsim's own Stage A must then fail to answer the question
from the redacted case (so retrieval really runs). Set B asks for a common vital or lab the case
never mentions. Both record the case's source article so the run step can exclude it.
"""

from __future__ import annotations

import json
import logging
import random
import threading
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from bench.schemas import (
    CaseFacts,
    CheckedFact,
    Item,
    QuestionSet,
    RedactorOutput,
    RejectedItem,
    Truth,
)
from bench.text import (
    background,
    case_text,
    check_redaction,
    patient_summary,
    slug,
    source_pmcid,
    with_redacted_text,
)
from bench.workspace import JsonlWriter, Workspace, read_models
from medsim import rules
from medsim.config import Settings
from medsim.errors import MedSimError
from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import CaseStudy, ChatMessage, LLMCallRecord
from medsim.stages.resolver import Resolver

logger = logging.getLogger("bench.items")

PmidLookup = Callable[[str], str | None]

REDACTOR_PROMPT = """\
You remove one measured value from a case report so that a patient simulator cannot see it.

You get the two text fields of the case and the TARGET measurement. Return both fields with \
every statement of the target value removed:
- Remove the value wherever it is stated for this measurement, including restatements (a heart \
rate repeated in an ECG description, a value repeated in a summary).
- Remove only what is needed: the number with its unit and label, and the clause if nothing \
else is left of it. Keep the grammar intact.
- Keep every other word, number, and finding exactly as written. Do not paraphrase, shorten, \
or add anything.
- Keep qualitative descriptions of the variable (e.g. "hypotensive", "anemic", "febrile") and \
list them in qualitative_mentions_kept.
- removed: the exact fragments you deleted.
Return only a JSON object with keys narrative, background_and_presentation, removed, \
qualitative_mentions_kept."""

# Set B variables: rules.VARIABLE_KEYWORDS key -> (question wording, category).
OPEN_VARIABLES: dict[str, tuple[str, str]] = {
    "temperature": ("body temperature", "vital_sign"),
    "heart_rate": ("heart rate", "vital_sign"),
    "respiratory_rate": ("respiratory rate", "vital_sign"),
    "blood_pressure": ("blood pressure", "vital_sign"),
    "oxygen_saturation": ("oxygen saturation", "vital_sign"),
    "glucose": ("blood glucose", "laboratory"),
    "hemoglobin": ("hemoglobin", "laboratory"),
    "white_cell_count": ("white blood cell count", "laboratory"),
    "platelet_count": ("platelet count", "laboratory"),
    "creatinine": ("serum creatinine", "laboratory"),
    "sodium": ("serum sodium", "laboratory"),
    "potassium": ("serum potassium", "laboratory"),
    "c_reactive_protein": ("C-reactive protein", "laboratory"),
    "lactate": ("serum lactate", "laboratory"),
}


@dataclass(frozen=True)
class _Candidate:
    item_id: str
    question_set: QuestionSet
    case_id: str
    variable: str
    category: str
    fact: CheckedFact | None = None


def question_for(variable: str, timepoint: str | None = None, *, past: bool = True) -> str:
    name = variable.strip()
    if not name[:2].isupper():  # keep acronyms such as "CRP" or "SpO2"
        name = name[:1].lower() + name[1:]
    when = f" {timepoint.strip()}" if timepoint and timepoint.strip() else ""
    return f"What {'was' if past else 'is'} the patient's {name}{when}?"


def order_set_a(facts: Iterable[CaseFacts], seed: int) -> list[_Candidate]:
    """Eligible facts, shuffled, then interleaved by category so the sample is balanced."""
    by_category: dict[str, list[_Candidate]] = defaultdict(list)
    for case_facts in facts:
        for fact in case_facts.facts:
            if fact.eligible:
                by_category[fact.category].append(
                    _Candidate(
                        item_id=f"A:{case_facts.case_id}:{slug(fact.variable)}",
                        question_set="A",
                        case_id=case_facts.case_id,
                        variable=fact.variable,
                        category=fact.category,
                        fact=fact,
                    )
                )
    rng = random.Random(seed)
    queues = []
    for category in sorted(by_category):
        queue = by_category[category]
        rng.shuffle(queue)
        queues.append(queue)
    ordered: list[_Candidate] = []
    while any(queues):
        for queue in queues:
            if queue:
                ordered.append(queue.pop(0))
    return ordered


def order_set_b(
    cases: dict[str, CaseStudy], facts: dict[str, CaseFacts], seed: int
) -> list[_Candidate]:
    """One variable per case the case never mentions, cycling through the variable list."""
    rng = random.Random(seed + 1)
    case_ids = sorted(cases)
    rng.shuffle(case_ids)
    mentioned: dict[str, set[str]] = {}
    for cid in case_ids:
        text = case_text(cases[cid])
        found = {var for _, _, var in rules.find_variables(text)}
        for fact in facts[cid].facts if cid in facts else []:
            if key := rules.canonical_variable(fact.variable):
                found.add(key)
        mentioned[cid] = found
    variables = list(OPEN_VARIABLES)
    rng.shuffle(variables)
    ordered: list[_Candidate] = []
    used: set[str] = set()
    progress = True
    while progress:
        progress = False
        for var in variables:
            pick = next((c for c in case_ids if c not in used and var not in mentioned[c]), None)
            if pick is None:
                continue
            used.add(pick)
            progress = True
            name, category = OPEN_VARIABLES[var]
            ordered.append(
                _Candidate(item_id=f"B:{pick}:{var}", question_set="B", case_id=pick,
                           variable=name, category=category)
            )  # fmt: skip
    return ordered


class ItemBuilder:
    def __init__(
        self,
        cases: dict[str, CaseStudy],
        *,
        llm: LLMClient,
        pipeline_llm: LLMClient,
        settings: Settings,
        redactor_model: str,
        redactor_max_tokens: int,
        lookup_pmid: PmidLookup,
    ) -> None:
        self.cases = cases
        self.llm = llm
        self.redactor_model = redactor_model
        self.redactor_max_tokens = redactor_max_tokens
        self.resolver = Resolver(
            pipeline_llm,
            model=settings.model_for("resolver"),
            max_tokens=settings.resolver_max_tokens,
        )
        self._lookup = lookup_pmid
        self._pmids: dict[str, str | None] = {}
        self._lock = threading.Lock()

    def source_ids(self, case_id: str) -> tuple[str | None, str | None]:
        pmcid = source_pmcid(case_id)
        if pmcid is None:
            return None, None
        with self._lock:
            if pmcid in self._pmids:
                return pmcid, self._pmids[pmcid]
        try:
            pmid = self._lookup(pmcid)
        except MedSimError as exc:
            logger.warning("PMID lookup for %s failed: %s", pmcid, exc)
            pmid = None
        with self._lock:
            self._pmids[pmcid] = pmid
        return pmcid, pmid

    def _reject(
        self, cand: _Candidate, reason: str, records: list[LLMCallRecord], **detail: Any
    ) -> RejectedItem:
        return RejectedItem(
            item_id=cand.item_id, question_set=cand.question_set, case_id=cand.case_id,
            variable=cand.variable, reason=reason, detail=detail, llm_calls=records,
        )  # fmt: skip

    def _stage_a_blocks(
        self, question: str, case: CaseStudy, records: list[LLMCallRecord]
    ) -> str | None:
        """Why Stage A would not send this question to retrieval, or None."""
        resolved = self.resolver.run(question, case, established_facts="(none)", records=records)
        if resolved.query_scope != "patient":
            return f"stage_a_scope_{resolved.query_scope}"
        if resolved.answerable_from_case:
            return "stage_a_answers_from_case"
        return None

    def build(self, cand: _Candidate) -> Item | RejectedItem:
        records: list[LLMCallRecord] = []
        try:
            return self._build_a(cand, records) if cand.fact else self._build_b(cand, records)
        except MedSimError as exc:
            return self._reject(cand, "llm_error", records, error=str(exc)[:300])

    def _build_a(self, cand: _Candidate, records: list[LLMCallRecord]) -> Item | RejectedItem:
        fact = cand.fact
        assert fact is not None
        case = self.cases[cand.case_id]
        target = {"variable": fact.variable, "value": fact.value, "unit": fact.unit,
                  "timepoint": fact.timepoint, "span": fact.span}  # fmt: skip
        fields = {"narrative": case.narrative, "background_and_presentation": background(case)}
        user = (
            f"TARGET MEASUREMENT:\n{json.dumps(target, ensure_ascii=False)}\n\n"
            f"CASE FIELDS:\n{json.dumps(fields, ensure_ascii=False, indent=1)}"
        )
        output = call_structured(
            self.llm, stage="redactor",
            messages=[ChatMessage(role="system", content=REDACTOR_PROMPT),
                      ChatMessage(role="user", content=user)],
            output_model=RedactorOutput, temperature=0.0, max_tokens=self.redactor_max_tokens,
            model=self.redactor_model, records=records,
        )  # fmt: skip
        redacted = with_redacted_text(
            case, output.narrative, output.background_and_presentation.strip()
        )
        failure = check_redaction(case_text(case), case_text(redacted), fact.span, fact.value)
        if failure:
            return self._reject(cand, failure, records, removed=output.removed)
        question = question_for(fact.variable, fact.timepoint)
        blocked = self._stage_a_blocks(question, redacted, records)
        if blocked:
            return self._reject(cand, blocked, records, question=question)
        pmcid, pmid = self.source_ids(cand.case_id)
        return Item(
            item_id=cand.item_id, question_set="A", case_id=cand.case_id,
            diagnosis=case.diagnosis, question=question, variable=fact.variable,
            category=fact.category, timepoint=fact.timepoint,
            characteristic_of_diagnosis=fact.characteristic_of_diagnosis,
            truth=Truth(value=fact.value, unit=fact.unit, span=fact.span),
            case=redacted, patient=patient_summary(redacted),
            source_pmcid=pmcid, source_pmid=pmid,
            kept_qualitative=output.qualitative_mentions_kept, removed_text=output.removed,
            llm_calls=records,
        )  # fmt: skip

    def _build_b(self, cand: _Candidate, records: list[LLMCallRecord]) -> Item | RejectedItem:
        case = self.cases[cand.case_id]
        question = question_for(cand.variable, past=False)
        blocked = self._stage_a_blocks(question, case, records)
        if blocked:
            return self._reject(cand, blocked, records, question=question)
        pmcid, pmid = self.source_ids(cand.case_id)
        return Item(
            item_id=cand.item_id, question_set="B", case_id=cand.case_id,
            diagnosis=case.diagnosis, question=question, variable=cand.variable,
            category=cand.category, case=case, patient=patient_summary(case),
            source_pmcid=pmcid, source_pmid=pmid, llm_calls=records,
        )  # fmt: skip


def _fill(
    target: int,
    candidates: Sequence[_Candidate],
    *,
    per_case: int,
    accepted_per_case: Counter[str],
    build: Callable[[_Candidate], Item | RejectedItem],
    items: JsonlWriter,
    rejected: JsonlWriter,
    workers: int,
) -> Counter[str]:
    """Build candidates in order, in parallel batches, until ``target`` items are accepted."""
    counts: Counter[str] = Counter()
    accepted = sum(accepted_per_case.values())
    queue = list(candidates)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        while accepted < target and queue:
            batch: list[_Candidate] = []
            planned = Counter(accepted_per_case)
            rest: list[_Candidate] = []
            for cand in queue:
                if len(batch) < target - accepted and planned[cand.case_id] < per_case:
                    batch.append(cand)
                    planned[cand.case_id] += 1
                else:
                    rest.append(cand)
            queue = rest
            if not batch:
                break
            for result in pool.map(build, batch):
                if isinstance(result, Item):
                    items.write(result)
                    accepted += 1
                    accepted_per_case[result.case_id] += 1
                    counts["accepted"] += 1
                    logger.info("item %s: %s", result.item_id, result.question)
                else:
                    rejected.write(result)
                    counts[f"rejected:{result.reason}"] += 1
                    logger.info("reject %s: %s", result.item_id, result.reason)
    counts["total_accepted"] = accepted
    return counts


def run_redact(
    ws: Workspace,
    cases: dict[str, CaseStudy],
    builder: ItemBuilder,
    *,
    set_a: int,
    set_b: int,
    per_case: int = 1,
    seed: int = 20260921,
    workers: int = 4,
) -> dict[str, Any]:
    facts = {f.case_id: f for f in read_models(ws.facts, CaseFacts) if f.status == "ok"}
    existing = read_models(ws.items, Item)
    seen = {i.item_id for i in existing} | {
        r.item_id for r in read_models(ws.rejected, RejectedItem)
    }
    items_writer, rejected_writer = JsonlWriter(ws.items), JsonlWriter(ws.rejected)
    summary: dict[str, Any] = {}
    for name, target, ordered in (
        ("A", set_a, order_set_a(facts.values(), seed)),
        ("B", set_b, order_set_b(cases, facts, seed)),
    ):
        already = Counter(i.case_id for i in existing if i.question_set == name)
        todo = [c for c in ordered if c.item_id not in seen]
        summary[name] = dict(
            _fill(target, todo, per_case=per_case, accepted_per_case=already,
                  build=builder.build, items=items_writer, rejected=rejected_writer,
                  workers=workers)
        )  # fmt: skip
        summary[name]["candidates"] = len(ordered)
    return summary
