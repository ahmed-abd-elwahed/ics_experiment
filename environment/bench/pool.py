"""Precomputed extract and redact over a whole case dataset.

``pool`` runs both steps once over every case and builds every possible question (every eligible
hidden value for set A; every case x never-mentioned variable for set B), then writes two
reusable files. ``sample`` picks a benchmark's questions from those files with the same seeded
ordering and rules as ``redact``, without any LLM call.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import subprocess
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bench.extract import SYSTEM_PROMPT as EXTRACTOR_PROMPT
from bench.extract import run_extract
from bench.items import (
    OPEN_VARIABLES,
    REDACTOR_PROMPT,
    ItemBuilder,
    _Candidate,
    all_set_b,
    order_set_a,
    order_set_b,
)
from bench.schemas import ELIGIBLE_CATEGORIES, CaseFacts, Item, RejectedItem
from bench.text import load_cases
from bench.workspace import JsonlWriter, Workspace, latest_by, read_jsonl, read_models
from medsim.errors import ConfigError
from medsim.llm.base import LLMClient
from medsim.models import CaseStudy, LLMCallRecord
from medsim.stages.resolver import SYSTEM_PROMPT as RESOLVER_PROMPT

logger = logging.getLogger("bench.pool")

FACTS_FORMAT = "bench-pool-facts"
ITEMS_FORMAT = "bench-pool-items"
POOL_VERSION = 1
RETRY_REASONS = frozenset({"llm_error"})  # rejections a rerun of ``pool`` tries again


# --- build --------------------------------------------------------------------------------------


def _latest_items(ws: Workspace) -> tuple[dict[str, Item], dict[str, RejectedItem]]:
    items = latest_by(read_models(ws.items, Item), lambda i: i.item_id)
    rejected = latest_by(read_models(ws.rejected, RejectedItem), lambda r: r.item_id)
    for item_id in items:  # accepted on a rerun after an earlier failure
        rejected.pop(item_id, None)
    return items, rejected


def build_items(
    ws: Workspace, candidates: Sequence[_Candidate], builder: ItemBuilder, *, workers: int
) -> Counter[str]:
    """Build every candidate not built yet (LLM errors are retried), in parallel."""
    items, rejected = _latest_items(ws)
    done = set(items) | {i for i, r in rejected.items() if r.reason not in RETRY_REASONS}
    todo = [c for c in candidates if c.item_id not in done]
    items_writer, rejected_writer = JsonlWriter(ws.items), JsonlWriter(ws.rejected)
    counts: Counter[str] = Counter(already_done=len(candidates) - len(todo))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(builder.build, cand) for cand in todo]
        for future in as_completed(futures):  # saved as each finishes, so a restart loses little
            result = future.result()
            if isinstance(result, Item):
                items_writer.write(result)
                counts[f"{result.question_set}:accepted"] += 1
            else:
                rejected_writer.write(result)
                counts[f"{result.question_set}:rejected:{result.reason}"] += 1
            done_now = sum(v for k, v in counts.items() if k != "already_done")
            if done_now % 50 == 0:
                logger.info("pool items: %d of %d built", done_now, len(todo))
    return counts


def run_pool(
    ws: Workspace,
    cases: dict[str, CaseStudy],
    *,
    llm: LLMClient,
    builder: ItemBuilder,
    extractor_model: str,
    extractor_max_tokens: int,
    workers: int,
) -> dict[str, Any]:
    extracted = run_extract(
        ws, cases, list(cases), llm=llm, model=extractor_model,
        max_tokens=extractor_max_tokens, workers=workers,
    )  # fmt: skip
    facts = {f.case_id: f for f in read_models(ws.facts, CaseFacts) if f.status == "ok"}
    candidates = [*order_set_a(facts.values(), seed=0), *all_set_b(cases, facts)]
    built = build_items(ws, candidates, builder, workers=workers)
    return {"extract": dict(extracted), "candidates": len(candidates), "items": dict(built)}


def _cost(records: Sequence[CaseFacts | Item | RejectedItem]) -> float:
    return round(sum(c.cost_usd or 0.0 for r in records for c in r.llm_calls), 6)


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _git() -> dict[str, Any]:
    def run(*args: str) -> str | None:
        try:
            done = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "uncommitted_changes": bool(status) if status is not None else None}  # fmt: skip


def _usage(records: Sequence[CaseFacts | Item | RejectedItem]) -> dict[str, Any]:
    """LLM calls per stage and model: counts, retries, failures, tokens, and cost."""
    calls: list[LLMCallRecord] = [c for r in records for c in r.llm_calls]
    groups: dict[str, list[LLMCallRecord]] = {}
    for call in calls:
        groups.setdefault(f"{call.stage}:{call.model}", []).append(call)
    return {
        key: {
            "stage": group[0].stage,
            "model": group[0].model,
            "calls": len(group),
            "retries": sum(c.attempt > 1 for c in group),
            "failed_calls": sum(not c.success for c in group),
            "prompt_tokens": sum(c.prompt_tokens or 0 for c in group),
            "completion_tokens": sum(c.completion_tokens or 0 for c in group),
            "cost_usd": round(sum(c.cost_usd or 0.0 for c in group), 6),
            "mean_latency_s": round(sum(c.latency_ms for c in group) / len(group) / 1000, 1),
        }
        for key, group in sorted(groups.items())
    }


def _started_at(ws: Workspace) -> str | None:
    """When the pool build started: the earliest ``pool`` log in the workspace."""
    logs = sorted((ws.root / "logs").glob("*_pool.log"))
    if not logs:
        return None
    stamp = logs[0].name.split("_", 1)[0]
    try:
        return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()
    except ValueError:
        return None


USAGE_NOTE = (
    "Per stage and model. calls counts every attempt; retries are attempts after the first "
    "(a reply cut off at max_tokens is retried once with double the budget, and transient "
    "provider errors are retried); failed_calls are attempts that did not return a usable "
    "reply, most of which succeeded on retry. Records that still failed are listed as "
    "failed_cases or with reason llm_error."
)
FACT_FIELDS = {
    "case_id": "Case id in the source dataset.",
    "diagnosis": "Ground-truth diagnosis (given to the extractor to judge "
    "characteristic_of_diagnosis).",
    "status": "ok, or error if extraction failed (failed cases are listed in "
    "metadata.statistics.failed_cases and have no entry).",
    "facts[].variable": "Standard clinical name of the measurement.",
    "facts[].value": "The number exactly as written in the case, without the unit.",
    "facts[].unit": "The unit exactly as written, or null.",
    "facts[].timepoint": "When it was measured (e.g. 'at presentation'), or null.",
    "facts[].span": "Shortest verbatim excerpt of the case containing the value.",
    "facts[].category": "vital_sign | laboratory | anthropometric | imaging_measurement | "
    "score_or_scale | medication_or_dose | other.",
    "facts[].askable_without_diagnosis": "Extractor's judgment: a clinician who does not know "
    "the diagnosis would plausibly ask for it.",
    "facts[].characteristic_of_diagnosis": "Extractor's judgment: typically abnormal in the "
    "diagnosis.",
    "facts[].eligible": "Usable as a hidden set A value (all deterministic checks passed).",
    "facts[].reject_reason": "Why not eligible (see metadata.rules.fact_reject_reasons).",
}
ITEM_FIELDS = {
    "item_id": "A:<case_id>:<variable slug> or B:<case_id>:<variable key>.",
    "question_set": "A: a value the case reports, removed from the case; B: a common vital or "
    "lab the case never mentions.",
    "case_id": "Case id in the source dataset.",
    "diagnosis": "Ground-truth diagnosis of the case.",
    "question": "The question medsim is asked.",
    "variable": "The measured variable asked about.",
    "category": "vital_sign | laboratory | anthropometric.",
    "timepoint": "Set A: when the hidden value was measured, or null.",
    "characteristic_of_diagnosis": "Set A: whether the variable is typically abnormal in the "
    "diagnosis.",
    "truth": "Set A: the hidden value {value, unit, span}; null for set B.",
    "case": "The case loaded into medsim: redacted (value removed) for set A, original for B.",
    "patient": "Patient description shown to the benchmark judge (redacted for set A).",
    "source_pmcid": "PMCID of the case's source article (from the case id), excluded from "
    "retrieval results during benchmark runs.",
    "source_pmid": "PMID of the source article, looked up via Europe PMC.",
    "kept_qualitative": "Set A: qualitative mentions of the variable kept in the case.",
    "removed_text": "Set A: the fragments the redactor removed.",
}
REJECTED_FIELDS = {
    "item_id": "As for items.",
    "question_set": "A or B.",
    "case_id": "Case id in the source dataset.",
    "variable": "The variable of the candidate question.",
    "reason": "Why the candidate was rejected (see metadata.rules.item_reject_reasons).",
    "detail": "Reason-specific detail (e.g. the question, or the removed fragments).",
}
RULES = {
    "eligible_categories": list(ELIGIBLE_CATEGORIES),
    "fact_reject_reasons": {
        "no_number": "The value has no digit.",
        "span_not_verbatim": "The quoted span is not verbatim in the case.",
        "value_not_in_span": "The value does not occur in its span.",
        "category:<name>": "Category not eligible (only vital signs, labs, body measurements).",
        "not_askable_without_diagnosis": "A clinician would not ask for it without knowing "
        "the diagnosis.",
        "variable_reported_more_than_once": "The case states this variable more than once, so "
        "hiding one value is ambiguous.",
    },
    "item_reject_reasons": {
        "span_still_present": "Set A: the value's span is still in the redacted case.",
        "value_still_present": "Set A: the value still occurs in the redacted case.",
        "numbers_added": "Set A: the redactor added a number.",
        "too_much_removed": "Set A: more text removed than max(3 x span length, 200 chars).",
        "text_added": "Set A: the redacted case is more than 20 characters longer.",
        "stage_a_answers_from_case": "medsim's Stage A resolver still answers the question from "
        "the (redacted) case, so no retrieval would run.",
        "stage_a_scope_<scope>": "Stage A classified the question as off_topic or withheld.",
        "llm_error": "An LLM call failed; retried on the next pool run.",
    },
    "set_b_variables": {key: name for key, (name, _category) in OPEN_VARIABLES.items()},
    "set_b_mentioned": "A variable counts as mentioned if medsim's variable rules find it in the "
    "case text or any extracted fact maps to it; set B uses only unmentioned variables.",
}
PROCEDURE = [
    "1. Load the source dataset (case_id, case_information, diagnosis); case_information is "
    "the case text.",
    "2. Extract (every case): the extractor LLM lists every numeric measurement of the patient "
    "(prompt in metadata.prompts.extractor); code then marks each value eligible or not "
    "(metadata.rules.fact_reject_reasons).",
    "3. Set A (every eligible value): the redactor LLM removes the value and any restatement "
    "(metadata.prompts.redactor); code checks the removal (span and value gone, no numbers "
    "added, little else changed); then medsim's Stage A resolver (metadata.prompts.resolver) "
    "must fail to answer the question from the redacted case.",
    "4. Set B (every case x common variable it never mentions): medsim's Stage A resolver must "
    "fail to answer the question from the original case.",
    "5. Each question records its source article (PMCID from the case id, PMID via Europe "
    "PMC) so benchmark runs can exclude it from retrieval.",
    "6. Export: the latest result per case and per candidate question; LLM call logs are "
    "summarised in metadata.statistics.llm_usage and left out of the records.",
]


DEFAULT_SEED = 20260921  # the redact step's default seed
SELECTION_RULE = [
    "Set A: at most one question per case. Candidates are walked in the redact step's seeded "
    "order, which interleaves vital signs, laboratory values, and body measurements; each "
    "case keeps its first accepted question. Cases without any accepted set A question get "
    "none (listed in metadata.selection.cases_without_set_a).",
    "Set B: exactly one question per case with any accepted set B question. Cases are taken "
    "in a seeded random order; each gets the variable used least so far among its accepted "
    "ones (ties broken by a seeded variable order), so the variables stay balanced.",
    "Every other candidate (accepted or rejected) is kept in the archive file "
    "(metadata.selection.archive_file).",
]


def select_per_case(
    items: dict[str, Item],
    facts: dict[str, CaseFacts],
    cases: dict[str, CaseStudy],
    *,
    seed: int = DEFAULT_SEED,
) -> list[Item]:
    """One set A question (when the case has one) and one set B question per case."""
    chosen: list[Item] = []
    with_a: set[str] = set()
    for cand in order_set_a(facts.values(), seed):
        if cand.case_id not in with_a and cand.item_id in items:
            chosen.append(items[cand.item_id])
            with_a.add(cand.case_id)
    rng = random.Random(seed + 2)
    case_ids = sorted(cases)
    rng.shuffle(case_ids)
    rank = {var: n for n, var in enumerate(rng.sample(list(OPEN_VARIABLES), len(OPEN_VARIABLES)))}
    by_case: dict[str, list[Item]] = {}
    for item in items.values():
        if item.question_set == "B":
            by_case.setdefault(item.case_id, []).append(item)
    used: Counter[str] = Counter()
    for cid in case_ids:
        options = by_case.get(cid)
        if not options:
            continue
        pick = min(options, key=lambda i: (used[_var_key(i)], rank.get(_var_key(i), 99)))
        used[_var_key(pick)] += 1
        chosen.append(pick)
    return chosen


def _var_key(item: Item) -> str:
    return item.item_id.rsplit(":", 1)[-1]  # B:<case_id>:<variable key>


def export_pool(
    ws: Workspace,
    cases: dict[str, CaseStudy],
    *,
    cases_file: Path,
    facts_file: Path,
    items_file: Path,
    all_items_file: Path,
    models: dict[str, str],
    processing: dict[str, Any] | None = None,
    notes: Sequence[str] = (),
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Write the facts file, the selected questions (one set A and one set B per case), and
    the archive of every candidate, from the workspace, with full metadata."""
    all_facts = read_models(ws.facts, CaseFacts)
    facts = latest_by((f for f in all_facts if f.status == "ok"), lambda f: f.case_id)
    missing = [cid for cid in cases if cid not in facts]
    items, rejected = _latest_items(ws)
    all_items: list[Item | RejectedItem] = [
        *read_models(ws.items, Item),
        *read_models(ws.rejected, RejectedItem),
    ]
    kept_facts = [facts[cid] for cid in cases if cid in facts]
    n_facts = sum(len(f.facts) for f in kept_facts)
    eligible = sum(x.eligible for f in kept_facts for x in f.facts)
    per_set = Counter(i.question_set for i in items.values())
    common: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "processing_started_at": _started_at(ws),
        "source_dataset": {"path": str(cases_file), "sha256": _sha256(cases_file),
                           "cases": len(cases),
                           "record_format": "{case_id, case_information, diagnosis}"},
        "code": {"repository_state": _git(), "module": "environment/bench/pool.py",
                 "command": "python -m bench pool", "pool_format_version": POOL_VERSION},
        "models": models,
        "processing": processing or {},
        "procedure": PROCEDURE,
        "rules": RULES,
        "prompts": {"extractor": EXTRACTOR_PROMPT, "redactor": REDACTOR_PROMPT,
                    "resolver": RESOLVER_PROMPT},
        "notes": list(notes),
    }  # fmt: skip

    facts_meta = {
        "title": "Measured values extracted from every case",
        "description": "Output of the benchmark's extract step over the whole source dataset: "
        "every numeric measurement of each patient, with a deterministic eligibility check "
        "for use as a hidden (set A) value.",
        "companion_files": [str(items_file), str(all_items_file)],
        **common,
        "record_fields": FACT_FIELDS,
        "statistics": {
            "cases_extracted": len(kept_facts), "failed_cases": missing,
            "facts": n_facts, "eligible_facts": eligible,
            "cases_with_eligible_facts": sum(any(x.eligible for x in f.facts) for f in kept_facts),
            "facts_by_category": dict(Counter(x.category for f in kept_facts for x in f.facts)),
            "fact_reject_reasons": dict(Counter(
                x.reject_reason for f in kept_facts for x in f.facts if x.reject_reason)),
            "llm_usage_note": USAGE_NOTE,
            "llm_usage": _usage(all_facts), "cost_usd": _cost(all_facts),
        },
    }  # fmt: skip
    order = {cid: n for n, cid in enumerate(cases)}

    def by_case(record: Item | RejectedItem) -> tuple[int, str]:
        return order.get(record.case_id, len(order)), record.item_id

    def stats(chosen: Sequence[Item], rejects: Sequence[RejectedItem]) -> dict[str, Any]:
        per_set = Counter(i.question_set for i in chosen)
        return {
            "questions": {"A": per_set["A"], "B": per_set["B"]},
            "cases_with_set_a": len({i.case_id for i in chosen if i.question_set == "A"}),
            "cases_with_set_b": len({i.case_id for i in chosen if i.question_set == "B"}),
            "set_a_by_category": dict(Counter(i.category for i in chosen
                                              if i.question_set == "A")),
            "set_b_by_variable": dict(Counter(i.variable for i in chosen
                                              if i.question_set == "B")),
            "rejected": {name: dict(Counter(r.reason for r in rejects if r.question_set == name))
                         for name in ("A", "B")},
        }  # fmt: skip

    everything = sorted(items.values(), key=by_case)
    rejects = sorted(rejected.values(), key=by_case)
    selected = sorted(select_per_case(items, facts, cases, seed=seed), key=by_case)
    without_a = [cid for cid in cases if cid not in {i.case_id for i in selected
                                                     if i.question_set == "A"}]  # fmt: skip
    usage = {"llm_usage_note": USAGE_NOTE, "llm_usage": _usage(all_items),
             "cost_usd": _cost(all_items)}  # fmt: skip

    items_meta = {
        "title": "Benchmark questions: one set A and one set B question per case",
        "description": "Output of the benchmark's redact step over the whole source dataset, "
        "reduced to one question per case and set: set A hides one eligible value from the "
        "case; set B asks for a common vital or lab the case never mentions. 'python -m bench "
        "sample' picks a benchmark's questions from this file without LLM calls. All other "
        "candidates are in the archive file.",
        "companion_files": [str(facts_file), str(all_items_file)],
        **common,
        "selection": {
            "rule": SELECTION_RULE, "seed": seed, "archive_file": str(all_items_file),
            "cases_without_set_a": without_a,
            "cases_without_set_a_explanation": "No eligible hidden value in the case (see "
            "the facts file's reject reasons), or every set A candidate of the case was "
            "rejected (see the archive file).",
        },
        "record_fields": {"items[]": ITEM_FIELDS,
                          "rejected[]": "Empty here; rejected candidates are in the archive."},
        "statistics": {**stats(selected, []),
                       "candidates_built": len(items) + len(rejected),
                       "note": "llm_usage and cost cover building every candidate, including "
                       "the archived ones.", **usage},
    }  # fmt: skip
    archive_meta = {
        "title": "Archive: every candidate benchmark question built from every case",
        "description": "Every candidate the redact step built over the whole source dataset "
        "(set A: every eligible hidden value; set B: every case x common variable it never "
        "mentions), accepted and rejected. The main items file keeps one question per case "
        "and set, selected from this archive; this file is kept for later use and also works "
        "with 'python -m bench sample --items-file'.",
        "companion_files": [str(facts_file), str(items_file)],
        **common,
        "selection": {"selected_into": str(items_file), "rule": SELECTION_RULE, "seed": seed},
        "record_fields": {"items[]": ITEM_FIELDS, "rejected[]": REJECTED_FIELDS},
        "statistics": {**stats(everything, rejects),
                       "candidates": len(items) + len(rejected), **usage},
    }  # fmt: skip
    facts_data = {
        "format": FACTS_FORMAT, "version": POOL_VERSION, "metadata": facts_meta,
        "cases": [f.model_dump(mode="json", exclude={"llm_calls"}) for f in kept_facts],
    }  # fmt: skip

    def dump(records: Sequence[Item | RejectedItem]) -> list[dict[str, Any]]:
        return [r.model_dump(mode="json", exclude={"llm_calls"}) for r in records]

    outputs = (
        (facts_file, facts_data),
        (items_file, {"format": ITEMS_FORMAT, "version": POOL_VERSION, "metadata": items_meta,
                      "items": dump(selected), "rejected": []}),
        (all_items_file, {"format": ITEMS_FORMAT, "version": POOL_VERSION,
                          "metadata": archive_meta, "items": dump(everything),
                          "rejected": dump(rejects)}),
    )  # fmt: skip
    for path, data in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    chosen = Counter(i.question_set for i in selected)
    return {
        "facts_file": str(facts_file), "items_file": str(items_file),
        "all_items_file": str(all_items_file),
        "cases_with_facts": len(kept_facts), "failed_cases": len(missing),
        "eligible_facts": eligible, "set_a": chosen["A"], "set_b": chosen["B"],
        "candidates_accepted": {"A": per_set["A"], "B": per_set["B"]},
        "rejected": len(rejected),
        "extract_cost_usd": facts_meta["statistics"]["cost_usd"],
        "redact_cost_usd": usage["cost_usd"],
    }  # fmt: skip


# --- sample -------------------------------------------------------------------------------------


def _read(path: Path, fmt: str) -> dict[str, Any]:
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Cannot read pool file {path}: {exc}") from exc
    if data.get("format") != fmt or data.get("version") != POOL_VERSION:
        raise ConfigError(f"{path} is not a version {POOL_VERSION} {fmt} file.")
    return data


def _pick(
    target: int,
    ordered: Sequence[_Candidate],
    *,
    per_case: int,
    items: dict[str, Item],
    rejected: dict[str, RejectedItem],
) -> tuple[list[Item], list[RejectedItem], int]:
    """Walk candidates in order as ``redact`` would, looking results up instead of building."""
    picked: list[Item] = []
    rejects: list[RejectedItem] = []
    per: Counter[str] = Counter()
    missing = 0
    for cand in ordered:
        if len(picked) >= target:
            break
        if per[cand.case_id] >= per_case:
            continue
        if cand.item_id in items:
            picked.append(items[cand.item_id])
            per[cand.case_id] += 1
        elif cand.item_id in rejected and rejected[cand.item_id].reason not in RETRY_REASONS:
            rejects.append(rejected[cand.item_id])
        else:
            missing += 1
    return picked, rejects, missing


def _with_case_fallback(ordered: Sequence[_Candidate], items: dict[str, Item]) -> list[_Candidate]:
    """After each set B candidate, the pool's other set B questions for the same case.

    A pool reduced to one question per case rarely holds the variable the seeded order picks,
    so the case's own question is used instead.
    """
    others: dict[str, list[Item]] = {}
    for item in items.values():
        if item.question_set == "B":
            others.setdefault(item.case_id, []).append(item)
    result: list[_Candidate] = []
    for cand in ordered:
        result.append(cand)
        result.extend(
            _Candidate(item_id=i.item_id, question_set="B", case_id=i.case_id,
                       variable=i.variable, category=i.category)
            for i in others.get(cand.case_id, []) if i.item_id != cand.item_id
        )  # fmt: skip
    return result


def run_sample(
    ws: Workspace,
    *,
    facts_file: Path,
    items_file: Path,
    set_a: int,
    set_b: int,
    per_case: int = 1,
    seed: int = 20260921,
    cases_file: Path | None = None,
) -> dict[str, Any]:
    if read_jsonl(ws.items) or read_jsonl(ws.rejected):
        raise ConfigError(f"{ws.root} already has questions; sample into a new workspace.")
    facts_data, items_data = _read(facts_file, FACTS_FORMAT), _read(items_file, ITEMS_FORMAT)
    cases_file = cases_file or Path(items_data["metadata"]["source_dataset"]["path"])
    cases = load_cases(cases_file)
    facts = {f["case_id"]: CaseFacts.model_validate(f) for f in facts_data["cases"]}
    items = {i["item_id"]: Item.model_validate(i) for i in items_data["items"]}
    rejected = {
        r["item_id"]: RejectedItem.model_validate(r) for r in items_data.get("rejected", [])
    }

    facts_writer = JsonlWriter(ws.facts)
    for case_facts in facts.values():
        facts_writer.write(case_facts)
    items_writer, rejected_writer = JsonlWriter(ws.items), JsonlWriter(ws.rejected)
    summary: dict[str, Any] = {"facts_file": str(facts_file), "items_file": str(items_file),
                               "seed": seed, "per_case": per_case,
                               "cases_file": str(cases_file)}  # fmt: skip
    for name, target, ordered in (
        ("A", set_a, order_set_a(facts.values(), seed)),
        ("B", set_b, _with_case_fallback(order_set_b(cases, facts, seed), items)),
    ):
        picked, rejects, missing = _pick(
            target, ordered, per_case=per_case, items=items, rejected=rejected
        )
        for item in picked:
            items_writer.write(item)
        for reject in rejects:
            rejected_writer.write(reject)
        summary[name] = {"accepted": len(picked), "rejected": len(rejects),
                         "not_in_pool": missing}  # fmt: skip
        if len(picked) < target:
            logger.warning("set %s: only %d of %d questions available", name, len(picked), target)
    return summary
