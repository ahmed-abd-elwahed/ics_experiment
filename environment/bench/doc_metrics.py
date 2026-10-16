"""Two metrics on the retrieved documents themselves, and the runs that search for the retrieval
settings that score highest on them.

- **Truth coverage** (set A): do the documents contain the hidden true value? *Strict*: a
  document gives a value or range for this variable in patients with the same or a closely
  related condition, and the true value lies inside that range or within about 15% of that
  value. *Category*: a document's value, range, or level (here a reference range that applies to
  such a patient also counts) puts the true value in the same low / normal / high category.
- **Graded relevance** (set A): each document is graded 0 (neither about the variable nor the
  patient's condition), 1 (about the variable or the condition, but no usable value), or 2
  (states a value, range, or level for the variable in patients comparable to this one).
  Summaries: nDCG@8 against a perfect list of eight grade-2 documents (so it rewards both better
  documents and a better order) and precision@8 (the share of grade-2 documents among eight).

One judge call per question and configuration grades all documents and gives both coverage
verdicts. Every positive verdict needs a verbatim quote that code finds in the document it names;
a grade 2 without one counts as 1, and a coverage verdict without one counts as not covered.

The configurations act on the retrieval only. Their runs reuse one frozen search query per
question (``queries``: medsim's Stages A and B once), so differences between configurations come
from the retrieval settings and not from the query writer's sampling, and no answer is written
(Stage C is not needed for these metrics). A configuration that changes the query writer has its
own frozen queries.

Steps (workspace ``environment/results/doc_metrics``)::

    python -m bench.doc_metrics queries [--query-set NAME]
    python -m bench.doc_metrics retrieve --configs baseline,q_natural,...
    python -m bench.doc_metrics judge --configs baseline,... [--stored 2-10] [--shuffled]
    python -m bench.doc_metrics score
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import random
import statistics
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from bench.config import BenchSettings
from bench.judge import Judge, _target, _truth
from bench.run import (
    RETRIEVAL_NOTES,
    RETRIEVAL_STAGES,
    LiveRetrievers,
    RetrieverFactory,
    SourceArticleFilter,
    _doc_record,
    _improved,
)
from bench.schemas import DocRecord, Item, RunRecord, Status, _LLMOutput, calls_cost
from bench.text import quote_found
from bench.workspace import JsonlWriter, Workspace, latest_by, read_models
from medsim import rules
from medsim.config import Settings, load_settings
from medsim.environment import build_aggregator, case_text
from medsim.errors import ConfigError, MedSimError
from medsim.llm.base import LLMClient
from medsim.llm.openrouter import OpenRouterClient
from medsim.models import ChatMessage, LiteratureQuery, LLMCallRecord
from medsim.retrieval.fulltext import FullTextFetcher
from medsim.retrieval.query_formulation import to_literature_query
from medsim.stages.query_builder import QueryBuilder
from medsim.stages.resolver import Resolver

logger = logging.getLogger("bench.doc_metrics")

RUBRIC = "d1"
K = 8  # documents per question: what Stage C reads
RESULTS = Path(__file__).resolve().parents[1] / "results"
REPO = RESULTS.parents[1]
WORKSPACE = RESULTS / "doc_metrics"
REPEATS = RESULTS / "repeats"
# The model of the stored benchmark runs, so the frozen queries match how they were made.
ENVIRONMENT_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_QUERY_SET = "base"


# --- configurations -------------------------------------------------------------------------------

Update = Callable[[Settings], Settings]


def _nested(field_name: str, **values: Any) -> Update:
    def update(s: Settings) -> Settings:
        inner = getattr(s, field_name).model_copy(update=values)
        return s.model_copy(update={field_name: inner})

    return update


def _top(**values: Any) -> Update:
    return lambda s: s.model_copy(update=values)


@dataclass(frozen=True)
class Change:
    """One setting changed from the baseline (medsim's default retrieval, changes 1-4)."""

    name: str
    description: str
    update: Update
    query_set: str | None = None  # frozen queries written by another query builder


CHANGES: dict[str, Change] = {
    c.name: c
    for c in (
        Change("q_natural", "LitSense natural-language queries",
               _nested("litsense", query_style="natural")),
        Change("q_synonym", "Europe PMC MeSH synonym expansion",
               _nested("europe_pmc", synonym=True)),
        Change("q_gpt6luna", "openai/gpt-6-luna writes the search query", lambda s: s,
               query_set="gpt-6-luna"),
        Change("epmc25", "25 Europe PMC candidates (baseline 50)",
               _nested("europe_pmc", page_size=25)),
        Change("epmc100", "100 Europe PMC candidates", _nested("europe_pmc", page_size=100)),
        Change("ls60", "60 LitSense results (baseline 30)", _nested("litsense", max_results=60)),
        Change("ls100", "100 LitSense results", _nested("litsense", max_results=100)),
        Change("ls_sentences", "LitSense sentences instead of passages",
               _nested("litsense", mode="sentences")),
        Change("no_value_first", "no value-first ranking", _top(rank_for_values=False)),
        Change("round_robin", "round-robin merge across sources instead of one list",
               _top(merge_strategy="round_robin")),
        Change("no_lexical_rerank", "no lexical rerank within each source",
               _top(rerank_documents=False)),
        Change("ls_no_rerank", "no LitSense-side rerank", _nested("litsense", rerank=False)),
        Change("llm_select20", "an LLM picks the 8 documents from the best 20",
               _top(llm_rerank=True, rerank_candidates=20)),
        Change("llm_select40", "an LLM picks the 8 documents from the best 40",
               _top(llm_rerank=True, rerank_candidates=40)),
        Change("no_population_filter", "no animal and age-group filter",
               _top(population_filter=False)),
        Change("no_excerpts", "no full-text excerpts (abstracts and passages only)",
               _top(fulltext_excerpts=False)),
        Change("fulltext20", "20 open-access full texts fetched for excerpts (baseline 10)",
               _top(fulltext_max_docs=20)),
        Change("chars3000", "3,000 characters per document (baseline 1,500)",
               _top(max_doc_chars=3000)),
        Change("ladder_v1", "the original broadening ladder (v1)", _top(ladder_version="v1")),
        Change("epmc_only", "Europe PMC only", _top(enabled_sources=["europe_pmc"])),
        Change("litsense_only", "LitSense only", _top(enabled_sources=["litsense"])),
    )
}  # fmt: skip
# "fresh1" and "fresh2" are the base query writer run again: new queries, for confirmation.
QUERY_SETS: dict[str, str | None] = {
    DEFAULT_QUERY_SET: None, "gpt-6-luna": "openai/gpt-6-luna", "fresh1": None, "fresh2": None
}  # fmt: skip


@dataclass(frozen=True)
class DocConfig:
    """The baseline, or the baseline with one or more changes (``a+b``), applied in order."""

    name: str
    changes: tuple[Change, ...]
    queries: str | None = None  # ``name@set``: run on another set of frozen queries

    @property
    def description(self) -> str:
        text = "; ".join(c.description for c in self.changes) or "baseline: changes 1-4"
        return text + (f" (queries: {self.queries})" if self.queries else "")

    @property
    def query_set(self) -> str:
        if self.queries:
            return self.queries
        sets = {c.query_set for c in self.changes if c.query_set}
        if len(sets) > 1:
            raise ConfigError(f"{self.name}: changes use different query writers")
        return sets.pop() if sets else DEFAULT_QUERY_SET

    def settings(self, base: Settings) -> Settings:
        settings = _improved()(base).model_copy(update={"max_documents": K})
        for change in self.changes:
            settings = change.update(settings)
        return settings


def doc_config(name: str) -> DocConfig:
    """``name#2`` is the same configuration under another label: with the search cache its
    documents are the same, so judging it again measures the judge's own noise."""
    spec, _, queries = name.partition("#")[0].partition("@")
    if queries and queries not in QUERY_SETS:
        raise ConfigError(f"Unknown query set {queries!r}; known: {', '.join(QUERY_SETS)}")
    if spec == "baseline":
        return DocConfig(name, (), queries or None)
    parts = spec.split("+")
    unknown = [p for p in parts if p not in CHANGES]
    if unknown:
        raise ConfigError(f"Unknown change(s) {', '.join(unknown)}; known: {', '.join(CHANGES)}")
    return DocConfig(name, tuple(CHANGES[p] for p in parts), queries or None)


def environment_settings(**overrides: Any) -> Settings:
    """medsim's settings for these runs: the stored runs' model, synchronous, cache on."""
    return load_settings(**{
        "default_model": ENVIRONMENT_MODEL, "resolver_model": None, "query_builder_model": None,
        "synthesizer_model": None, "reranker_model": None, "cache_enabled": True,
        "ledger_enabled": False, **overrides,
    })  # fmt: skip


# --- frozen queries -------------------------------------------------------------------------------


class FrozenQuery(BaseModel):
    item_id: str
    query_set: str
    model: str
    status: Status
    error: str | None = None
    path: str | None = None  # "query": a literature query; else why there is none
    literature_query: LiteratureQuery | None = None
    partial_facts: list[str] = Field(default_factory=list)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


def build_query(item: Item, *, llm: LLMClient, settings: Settings, query_set: str) -> FrozenQuery:
    """medsim's Stages A and B for one question, as the environment runs them."""
    model = QUERY_SETS[query_set] or settings.model_for("query_builder")
    base: dict[str, Any] = {"item_id": item.item_id, "query_set": query_set, "model": model}
    records: list[LLMCallRecord] = []
    try:
        resolved = Resolver(
            llm, model=settings.model_for("resolver"), max_tokens=settings.resolver_max_tokens
        ).run(item.question, item.case, established_facts="(none)", records=records)
        if resolved.query_scope in ("off_topic", "withheld"):
            return FrozenQuery(**base, status="ok", path=resolved.query_scope, llm_calls=records)
        if resolved.answerable_from_case and resolved.answer:
            return FrozenQuery(**base, status="ok", path="case_study", llm_calls=records)
        built = QueryBuilder(llm, model=model, max_tokens=settings.query_builder_max_tokens).run(
            item.question, item.case, partial_facts=resolved.partial_facts, records=records
        )
    except MedSimError as exc:
        return FrozenQuery(**base, status="error", error=str(exc)[:500], llm_calls=records)
    if built.literature_query is None:
        return FrozenQuery(**base, status="ok", path="query_builder_declined", llm_calls=records)
    lq = to_literature_query(built).model_copy(
        update={"patient_age_group": rules.age_group(case_text(item.case))}
    )
    return FrozenQuery(
        **base, status="ok", path="query", literature_query=lq,
        partial_facts=list(resolved.partial_facts), llm_calls=records,
    )  # fmt: skip


# --- retrieval only -------------------------------------------------------------------------------

FullTextFactory = Callable[[Settings], FullTextFetcher]


def retrieve_one(
    item: Item,
    config: DocConfig,
    query: FrozenQuery,
    *,
    llm: LLMClient,
    base_settings: Settings,
    retrievers: RetrieverFactory,
    fulltext: FullTextFactory | None = None,
) -> RunRecord:
    """The documents one configuration retrieves for a frozen query; no answer is written."""
    settings = config.settings(base_settings)
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    started = time.perf_counter()
    base: dict[str, Any] = {"item_id": item.item_id, "config": config.name,
                            "question_set": item.question_set,
                            "started_at": started_at}  # fmt: skip
    if query.literature_query is None:
        return RunRecord(**base, status="ok", wall_time_s=0.0, path=query.path)
    filters = [
        SourceArticleFilter(r, pmcid=item.source_pmcid, pmid=item.source_pmid)
        for r in retrievers(settings)
    ]
    aggregator = build_aggregator(
        settings, filters, llm,
        fulltext=fulltext(settings) if fulltext and settings.fulltext_excerpts else None,
    )  # fmt: skip
    records: list[LLMCallRecord] = []
    try:
        result, params = aggregator.search(query.literature_query, records=records)
    except MedSimError as exc:
        return RunRecord(
            **base, status="error", error=f"{type(exc).__name__}: {exc}"[:500],
            wall_time_s=round(time.perf_counter() - started, 2),
        )  # fmt: skip
    attempts = {
        source: list(info.get("query_attempts", []))
        for source, info in (params.get("per_source") or {}).items()
    }
    cost = sum(float(a.get("cost_usd") or 0.0) for source in attempts.values() for a in source)
    cost += sum(c.cost_usd or 0.0 for c in records if c.stage in RETRIEVAL_STAGES)
    failed = list(params.get("failed_sources") or [])
    status: Status = "error" if filters and len(failed) == len(filters) else "ok"
    return RunRecord(
        **base, status=status, error="all sources failed" if status == "error" else None,
        wall_time_s=round(time.perf_counter() - started, 2), path="retrieval_only",
        literature_query=result.query,
        documents=[_doc_record(i + 1, d) for i, d in enumerate(result.documents)],
        excluded_source_docs=[d for f in filters for d in f.excluded], failed_sources=failed,
        source_errors=list(result.errors), query_attempts=attempts, llm_calls=records,
        retrieval_cost_usd=round(cost, 6),
        retrieval_notes={k: params[k] for k in RETRIEVAL_NOTES if k in params},
    )  # fmt: skip


# --- the judge ------------------------------------------------------------------------------------

PROMPT = """\
You grade the documents a patient simulator retrieved from the literature to answer one \
question about one patient. You see the QUESTION, the TARGET VARIABLE, the DIAGNOSIS, a short \
PATIENT description, the TRUE VALUE (hidden from the simulator), and the numbered DOCUMENTS. \
Judge only from the documents, not from what you know.

Fields:
- documents: one object per document, in order, with keys rank (its number), grade, and quote.
  - grade 2: the document states a value, a range, or an explicit level ("normal", "markedly \
elevated") for the TARGET VARIABLE in patients comparable to this one: this or a closely related \
condition, or a reference range that applies to such a patient.
  - grade 1: the document is about the TARGET VARIABLE or about the patient's condition, but \
gives no such value for comparable patients.
  - grade 0: neither.
  - quote: for grade 2, the passage that states the value, copied exactly from that document \
(at most 40 words, no ellipsis); "" otherwise.
- strict: true if at least one document gives a value or a range for the TARGET VARIABLE in \
patients with this or a closely related condition (a general reference range for healthy people \
does not count here), and the TRUE VALUE lies inside that range or within about 15% of that value.
- category: true if at least one document gives a value, a range, or an explicit level for the \
TARGET VARIABLE in comparable patients (here a reference range that applies to such a patient \
counts) that puts the TRUE VALUE in the same category (low, normal, or high) as the document does.
- coverage_rank: the number of the document that best supports strict, or else category; null \
if neither.
- coverage_quote: the passage of that document that shows it, copied exactly (at most 40 words, \
no ellipsis); "" if neither.
- rationale: one sentence.
Return only a JSON object with exactly these keys."""


class GradeOutput(BaseModel):
    rank: int
    grade: Literal[0, 1, 2]
    quote: str


class DocJudgeOutput(_LLMOutput):
    documents: list[GradeOutput]
    strict: bool
    category: bool
    coverage_rank: int | None
    coverage_quote: str
    rationale: str


class DocJudgment(BaseModel):
    """One judge's grades of one question's documents under one configuration.

    ``grades`` and the coverage flags are after the quote checks; ``output`` is the reply.
    """

    item_id: str
    config: str
    docs_key: str
    judge_model: str
    rubric: str
    status: Status
    error: str | None = None
    control: str | None = None  # "shuffled": the documents belong to another question
    grades: list[int] = Field(default_factory=list)
    strict: bool = False
    category: bool = False
    quote_failures: int = 0
    output: DocJudgeOutput | None = None
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


def docs_key(documents: Sequence[DocRecord]) -> str:
    digest = hashlib.sha256()
    for doc in documents:
        digest.update(f"{doc.rank}\x1f{doc.doc_id}\x1f{doc.text}\x1e".encode())
    return digest.hexdigest()[:16]


def documents_text(documents: Sequence[DocRecord]) -> str:
    return "\n\n".join(
        f"[{i}] {doc.title or '(no title)'}\n{doc.text}" for i, doc in enumerate(documents, 1)
    )


def judge_messages(item: Item, documents: Sequence[DocRecord]) -> list[ChatMessage]:
    user = (
        f"QUESTION: {item.question}\nTARGET VARIABLE: {_target(item)}\n"
        f"DIAGNOSIS: {item.diagnosis}\nPATIENT: {item.patient}\nTRUE VALUE: {_truth(item)}\n\n"
        f"DOCUMENTS:\n{documents_text(documents)}"
    )
    return [ChatMessage(role="system", content=PROMPT), ChatMessage(role="user", content=user)]


def checked(
    out: DocJudgeOutput, documents: Sequence[DocRecord]
) -> tuple[list[int], bool, bool, int]:
    """Grades and coverage after the quote checks, and how many quotes failed."""
    by_rank = {g.rank: g for g in out.documents}
    grades: list[int] = []
    failures = 0
    for i, doc in enumerate(documents, 1):
        g = by_rank.get(i)
        grade = g.grade if g else 0
        if grade == 2 and not (g and quote_found(g.quote, doc.text)):
            grade, failures = 1, failures + 1
        grades.append(grade)
    covered = out.strict or out.category
    rank = out.coverage_rank
    quote_ok = (
        covered and rank is not None and 1 <= rank <= len(documents)
        and quote_found(out.coverage_quote, documents[rank - 1].text)
    )  # fmt: skip
    if covered and not quote_ok:
        failures += 1
    strict = bool(out.strict and quote_ok)
    return grades, strict, bool((out.category or out.strict) and quote_ok), failures


def judge_documents(
    judge: Judge,
    item: Item,
    config: str,
    documents: Sequence[DocRecord],
    *,
    control: str | None = None,
    own_documents: Sequence[DocRecord] | None = None,
) -> DocJudgment:
    """``own_documents``: for a control, the question's own documents, whose key is stored so
    that a rerun finds the judgment done."""
    key = docs_key(documents if own_documents is None else own_documents)
    base: dict[str, Any] = {
        "item_id": item.item_id, "config": config, "docs_key": key,
        "judge_model": judge.model, "rubric": RUBRIC, "control": control,
    }  # fmt: skip
    if not documents:  # nothing retrieved: nothing covers, nothing to grade
        return DocJudgment(**base, status="ok")
    records: list[LLMCallRecord] = []
    try:
        out: DocJudgeOutput = judge._call(judge_messages(item, documents), DocJudgeOutput, records)
    except MedSimError as exc:
        return DocJudgment(**base, status="error", error=str(exc)[:300], llm_calls=records)
    grades, strict, category, failures = checked(out, documents)
    return DocJudgment(
        **base, status="ok", grades=grades, strict=strict, category=category,
        quote_failures=failures, output=out, llm_calls=records,
    )  # fmt: skip


# --- scores ---------------------------------------------------------------------------------------

IDEAL_DCG = sum(2 / math.log2(i + 1) for i in range(1, K + 1))


def ndcg(grades: Sequence[int]) -> float:
    """DCG@8 of the grades in retrieved order over that of eight grade-2 documents."""
    return sum(g / math.log2(i + 1) for i, g in enumerate(grades[:K], 1)) / IDEAL_DCG


def precision(grades: Sequence[int]) -> float:
    return sum(g == 2 for g in grades[:K]) / K


METRICS = ("strict", "category", "ndcg", "precision")


def question_scores(j: DocJudgment) -> dict[str, float]:
    return {"strict": float(j.strict), "category": float(j.category),
            "ndcg": ndcg(j.grades), "precision": precision(j.grades)}  # fmt: skip


def bootstrap_ci(
    values: Sequence[float], *, reps: int = 2000, seed: int = 7
) -> tuple[float, float]:
    """95% percentile interval of the mean, resampling questions."""
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(reps))
    return means[int(0.025 * reps)], means[int(0.975 * reps) - 1]


def summarize(judgments: Mapping[str, DocJudgment], expected: Sequence[str]) -> dict[str, Any]:
    """Means over the expected questions; a question with no judgment yet is left out and
    counted, a question whose retrieval found nothing scores zero."""
    found = [judgments[i] for i in expected if i in judgments]
    per = [question_scores(j) for j in found]
    out: dict[str, Any] = {"questions": len(found), "missing": len(expected) - len(found)}
    for metric in METRICS:
        values = [p[metric] for p in per]
        out[metric] = statistics.fmean(values) if values else 0.0
        out[f"{metric}_ci"] = bootstrap_ci(values)
    out["quote_failures"] = sum(j.quote_failures for j in found)
    out["judge_cost_usd"] = round(sum(calls_cost(j.llm_calls) for j in found), 4)
    return out


def paired_difference(
    a: Mapping[str, DocJudgment], b: Mapping[str, DocJudgment], metric: str
) -> dict[str, Any]:
    """Mean of b - a over the questions both have, with a 95% bootstrap interval."""
    common = sorted(set(a) & set(b))
    diffs = [question_scores(b[i])[metric] - question_scores(a[i])[metric] for i in common]
    low, high = bootstrap_ci(diffs)
    return {"n": len(common), "mean": statistics.fmean(diffs) if diffs else 0.0,
            "ci": (low, high)}  # fmt: skip


# --- workspace ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class DocWorkspace:
    root: Path = WORKSPACE

    @property
    def queries(self) -> Path:
        return self.root / "queries.jsonl"

    def run_file(self, config: str) -> Path:
        return self.root / "runs" / f"{config}.jsonl"

    @property
    def judgments(self) -> Path:
        return self.root / "judge" / "doc_grades.jsonl"

    @property
    def scores(self) -> Path:
        return self.root / "scores.json"


def set_a_items(path: Path = REPEATS / "run_02" / "sets_ab" / "items.jsonl") -> list[Item]:
    return [i for i in read_models(path, Item) if i.question_set == "A" and i.truth is not None]


def frozen_queries(ws: DocWorkspace, query_set: str) -> dict[str, FrozenQuery]:
    latest = latest_by(
        (q for q in read_models(ws.queries, FrozenQuery) if q.query_set == query_set),
        lambda q: q.item_id,
    )
    return {k: q for k, q in latest.items() if q.status == "ok"}


def stored_label(run: int, config: str) -> str:
    return f"stored_run{run:02d}_{config}"


def stored_runs(run: int, config: str) -> dict[str, RunRecord]:
    ws = Workspace(REPEATS / f"run_{run:02d}" / "sets_ab")
    latest = latest_by(read_models(ws.run_file(config), RunRecord), lambda r: r.item_id)
    return {k: r for k, r in latest.items() if r.status == "ok" and r.question_set == "A"}


def config_runs(ws: DocWorkspace, label: str) -> dict[str, RunRecord]:
    if label.startswith("stored_run"):
        run, _, config = label.removeprefix("stored_run").partition("_")
        return stored_runs(int(run), config)
    latest = latest_by(read_models(ws.run_file(label), RunRecord), lambda r: r.item_id)
    return {k: r for k, r in latest.items() if r.status == "ok"}


def ok_judgments(
    ws: DocWorkspace, label: str, judge_model: str, *, control: str | None = None
) -> dict[str, DocJudgment]:
    """The latest successful judgment per question of a configuration's current documents."""
    runs = config_runs(ws, label)
    keys = {i: docs_key(r.documents) for i, r in runs.items()}
    found: dict[str, DocJudgment] = {}
    for j in read_models(ws.judgments, DocJudgment):
        if (j.config == label and j.judge_model == judge_model and j.rubric == RUBRIC
                and j.status == "ok" and j.control == control
                and keys.get(j.item_id) == j.docs_key):  # fmt: skip
            found[j.item_id] = j
    return found


def shuffled(item_ids: Sequence[str], seed: int = 11) -> dict[str, str]:
    """Each question paired with another question's documents (a derangement)."""
    ids = list(item_ids)
    if len(ids) < 2:
        return {}
    rng = random.Random(seed)
    order = ids[:]
    while True:
        rng.shuffle(order)
        if all(a != b for a, b in zip(ids, order, strict=True)):
            return dict(zip(ids, order, strict=True))


# --- steps ----------------------------------------------------------------------------------------


def _pool(
    jobs: Sequence[Callable[[], BaseModel]], writer: JsonlWriter, workers: int, label: str
) -> Counter[str]:
    """Run the jobs in parallel; stops starting new ones once the key or account refuses."""
    counts: Counter[str] = Counter()
    refused = threading.Event()
    cost = 0.0

    def guarded(fn: Callable[[], BaseModel]) -> BaseModel | None:
        return None if refused.is_set() else fn()

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(guarded, fn) for fn in jobs]
        for n, future in enumerate(as_completed(futures), 1):
            record = future.result()
            if record is None:
                counts["skipped"] += 1
                continue
            writer.write(record)
            status = str(getattr(record, "status", "ok"))
            counts[status] += 1
            cost += calls_cost(getattr(record, "llm_calls", []))
            error = str(getattr(record, "error", "") or "")
            if status == "error" and any(code in error for code in ("402", "403")):
                if not refused.is_set():
                    logger.error("%s: the key or account refused a call (%s); stopping",
                                 label, error[:120])  # fmt: skip
                refused.set()
            if n % 25 == 0 or n == len(futures):
                logger.info("%s: %d/%d, $%.4f", label, n, len(futures), cost)
    counts["cost_millicents"] = round(cost * 100_000)
    return counts


def step_queries(
    ws: DocWorkspace, items: Sequence[Item], query_set: str, *, llm: LLMClient,
    settings: Settings, workers: int, limit: int | None = None,
) -> Counter[str]:  # fmt: skip
    done = frozen_queries(ws, query_set)
    todo = [i for i in items if i.item_id not in done][:limit]
    jobs = [lambda i=i: build_query(i, llm=llm, settings=settings, query_set=query_set)
            for i in todo]  # fmt: skip
    return _pool(jobs, JsonlWriter(ws.queries), workers, f"queries {query_set}")


def step_retrieve(
    ws: DocWorkspace, items: Sequence[Item], config: DocConfig, *, llm: LLMClient,
    settings: Settings, live: LiveRetrievers, workers: int, limit: int | None = None,
) -> Counter[str]:  # fmt: skip
    queries = frozen_queries(ws, config.query_set)
    missing = [i.item_id for i in items if i.item_id not in queries]
    if missing:
        raise ConfigError(
            f"{config.name}: {len(missing)} questions have no frozen query in set "
            f"{config.query_set!r}; run `queries --query-set {config.query_set}` first."
        )
    # A question where a source failed (an outage, a rate limit) is retrieved again.
    done = {k for k, r in config_runs(ws, config.name).items() if not r.failed_sources}
    todo = [i for i in items if i.item_id not in done][:limit]
    jobs = [
        lambda i=i: retrieve_one(
            i,
            config,
            queries[i.item_id],
            llm=llm,
            base_settings=settings,
            retrievers=live,
            fulltext=live.fulltext,
        )
        for i in todo
    ]
    return _pool(jobs, JsonlWriter(ws.run_file(config.name)), workers, f"retrieve {config.name}")


def step_judge(
    ws: DocWorkspace, items: Sequence[Item], label: str, judge: Judge, *, workers: int,
    control: str | None = None, limit: int | None = None,
) -> Counter[str]:  # fmt: skip
    runs = config_runs(ws, label)
    by_id = {i.item_id: i for i in items}
    ids = [i for i in by_id if i in runs]
    done = ok_judgments(ws, label, judge.model, control=control)
    partner = shuffled(ids) if control == "shuffled" else {i: i for i in ids}
    todo = [i for i in ids if i not in done][:limit]
    jobs = [
        lambda i=i: judge_documents(
            judge,
            by_id[i],
            label,
            runs[partner[i]].documents,
            control=control,
            own_documents=runs[i].documents,
        )
        for i in todo
    ]
    name = f"judge {label}" + (f" ({control})" if control else "")
    return _pool(jobs, JsonlWriter(ws.judgments), workers, name)


def step_score(ws: DocWorkspace, items: Sequence[Item], judge_model: str) -> dict[str, Any]:
    labels = sorted({j.config for j in read_models(ws.judgments, DocJudgment)})
    expected = [i.item_id for i in items]
    results: dict[str, Any] = {"judge_model": judge_model, "rubric": RUBRIC, "configs": {}}
    baseline = ok_judgments(ws, "baseline", judge_model) if "baseline" in labels else {}
    for label in labels:
        for control in (None, "shuffled"):
            judged = ok_judgments(ws, label, judge_model, control=control)
            if not judged:
                continue
            key = label + (" (shuffled)" if control else "")
            entry = summarize(judged, expected)
            runs = config_runs(ws, label)
            entry["description"] = (
                doc_config(label).description
                if not label.startswith("stored_")
                else "stored benchmark run (fresh query, full pipeline)"
            )
            entry["retrieval_cost_usd"] = round(sum(r.retrieval_cost_usd for r in runs.values()), 4)
            entry["documents_per_question"] = (
                statistics.fmean(len(r.documents) for r in runs.values()) if runs else 0.0
            )
            # A configuration on another query set is compared with the baseline on that set.
            ref_label = "baseline@" + label.partition("@")[2] if "@" in label else "baseline"
            ref = (
                baseline
                if ref_label == "baseline"
                else (ok_judgments(ws, ref_label, judge_model) if ref_label in labels else {})
            )
            if ref and control is None and label != ref_label:
                entry["vs_baseline"] = {m: paired_difference(ref, judged, m) for m in METRICS}
            results["configs"][key] = entry
    ws.scores.parent.mkdir(parents=True, exist_ok=True)
    ws.scores.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def table(results: Mapping[str, Any]) -> str:
    lines = ["| Configuration | Strict coverage | Category coverage | nDCG@8 | Precision@8 | "
             "Δ strict vs baseline | n |", "|---|---|---|---|---|---|---|"]  # fmt: skip
    rows = sorted(results["configs"].items(), key=lambda kv: (-kv[1]["strict"], -kv[1]["ndcg"]))
    for name, s in rows:
        d = s.get("vs_baseline", {}).get("strict")
        delta = (
            f"{100 * d['mean']:+.1f} ({100 * d['ci'][0]:+.1f} to {100 * d['ci'][1]:+.1f})"
            if d
            else ""
        )
        lines.append(
            f"| {name} | {100 * s['strict']:.1f}% | {100 * s['category']:.1f}% | "
            f"{s['ndcg']:.3f} | {100 * s['precision']:.1f}% | {delta} | {s['questions']} |"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bench.doc_metrics", description=__doc__)
    parser.add_argument("step", choices=["queries", "retrieve", "judge", "score"])
    parser.add_argument("--configs", default="baseline",
                        help="Comma-separated: baseline, a change, or changes joined "
                        "by +.")  # fmt: skip
    parser.add_argument("--query-set", default=DEFAULT_QUERY_SET, choices=list(QUERY_SETS))
    parser.add_argument("--stored", help='Also judge stored runs\' documents, e.g. "2-10".')
    parser.add_argument("--stored-config", default="improved_1to4")
    parser.add_argument("--shuffled", action="store_true",
                        help="Judge each question against another question's "
                        "documents.")  # fmt: skip
    parser.add_argument("--judge", help="Judge model; default: the panel's main judge.")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--limit", type=int, help="At most this many questions per step.")
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    args = parser.parse_args(argv)

    ws = DocWorkspace(args.workspace)
    (ws.root / "logs").mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    handler = logging.FileHandler(ws.root / "logs" / f"{stamp}_{args.step}.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger("bench").setLevel(logging.INFO)
    logger.info("doc_metrics %s", " ".join(sys.argv[1:] if argv is None else argv))

    bench = BenchSettings()
    judge_model = args.judge or bench.judge_model
    items = set_a_items()
    if args.step == "score":
        results = step_score(ws, items, judge_model)
        print(table(results))
        return 0
    settings = environment_settings()
    llm = OpenRouterClient(settings)
    summary: dict[str, Any] = {}
    try:
        if args.step == "queries":
            model = QUERY_SETS[args.query_set]
            llm.verify_models([ENVIRONMENT_MODEL, *([model] if model else [])])
            summary[args.query_set] = step_queries(
                ws, items, args.query_set, llm=llm, settings=settings, workers=args.workers,
                limit=args.limit,
            )  # fmt: skip
        elif args.step == "retrieve":
            live = LiveRetrievers(settings, cache=True)
            try:
                for name in args.configs.split(","):
                    summary[name] = step_retrieve(
                        ws, items, doc_config(name), llm=llm, settings=settings, live=live,
                        workers=args.workers, limit=args.limit,
                    )  # fmt: skip
            finally:
                live.close()
        else:
            llm.verify_models([judge_model])
            judge = Judge(llm, judge_model, bench.judge_max_tokens,
                          max_attempts=bench.judge_max_attempts,
                          backoff_s=bench.judge_retry_backoff_s)  # fmt: skip
            labels = [] if args.configs == "" else args.configs.split(",")
            if args.stored:
                first, _, last = args.stored.partition("-")
                labels += [stored_label(r, args.stored_config)
                           for r in range(int(first), int(last or first) + 1)]  # fmt: skip
            for label in labels:
                control = "shuffled" if args.shuffled else None
                summary[label] = step_judge(
                    ws, items, label, judge, workers=args.workers, control=control,
                    limit=args.limit,
                )  # fmt: skip
    finally:
        llm.close()
    logger.info("summary: %s", json.dumps(summary, default=dict))
    print(json.dumps(summary, indent=1, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
