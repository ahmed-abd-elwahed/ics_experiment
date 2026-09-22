"""Step 3: ask medsim every question under each retrieval configuration.

Each configuration is a retrieval method. The case's own source article is filtered out of every
source's results before merging (it would leak the hidden value), and the filtered documents are
recorded so the leak rate can be reported.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from bench.schemas import DocRecord, Item, RunRecord, calls_cost
from bench.workspace import JsonlWriter, Workspace, latest_by, read_models
from medsim.config import Settings
from medsim.environment import MedicalEnvironment, build_aggregator
from medsim.errors import MedSimError
from medsim.http_utils import RateLimiter
from medsim.llm.base import LLMClient
from medsim.models import (
    EnvironmentResponse,
    LiteratureQuery,
    LiteratureSearchResult,
    LLMCallRecord,
    RetrievedDocument,
)
from medsim.retrieval.aggregator import RetrievalAggregator
from medsim.retrieval.base import Retriever, strip_html
from medsim.retrieval.cache import ResponseCache
from medsim.retrieval.europe_pmc import EuropePMCRetriever
from medsim.retrieval.fulltext import FullTextFetcher
from medsim.retrieval.litsense import LitSenseRetriever
from medsim.retrieval.openrouter_search import OpenRouterSearchRetriever, identifiers_from_url
from medsim.retrieval.query_formulation import REFERENCE_TERMS

logger = logging.getLogger("bench.run")

RetrieverFactory = Callable[[Settings], list[Retriever]]
FullTextFactory = Callable[[Settings], FullTextFetcher]

# LLM calls made during retrieval: their cost is retrieval cost, not medsim Stage A-C cost.
RETRIEVAL_STAGES = frozenset({"reranker"})
RETRIEVAL_NOTES = ("population_filtered", "patient_age_group", "excerpts", "llm_rerank")


# --- configurations -----------------------------------------------------------------------------


@dataclass(frozen=True)
class RunConfig:
    name: str
    description: str
    update: Callable[[Settings], Settings] = field(default=lambda s: s)
    condition_blind: bool = False  # search for the variable's reference range, not the diagnosis

    def settings(self, base: Settings) -> Settings:
        return self.update(base)


def _sources(*names: str) -> Callable[[Settings], Settings]:
    return lambda s: s.model_copy(update={"enabled_sources": list(names)})


# Retrieval as first evaluated: changes 1-6 off, 25 Europe PMC candidates. medsim's defaults
# now include changes 1-4, so configurations of the original method set this explicitly.
ORIGINAL_RETRIEVAL: dict[str, Any] = {
    "rank_for_values": False,
    "merge_strategy": "round_robin",
    "population_filter": False,
    "ladder_version": "v1",
    "fulltext_excerpts": False,
    "llm_rerank": False,
}


def _original(*sources: str) -> Callable[[Settings], Settings]:
    def update(s: Settings) -> Settings:
        s = _sources(*sources)(s)
        return s.model_copy(
            update={
                **ORIGINAL_RETRIEVAL,
                "europe_pmc": s.europe_pmc.model_copy(update={"page_size": 25}),
                "litsense": s.litsense.model_copy(update={"query_style": "keywords"}),
            }
        )

    return update


def _improved(
    *, natural_litsense: bool = False, llm_rerank: bool = False
) -> Callable[[Settings], Settings]:
    """Retrieval changes 1-4 (results/README.md), optionally with 5 and 6."""

    def update(s: Settings) -> Settings:
        s = _original("europe_pmc", "litsense")(s)
        return s.model_copy(
            update={
                "europe_pmc": s.europe_pmc.model_copy(update={"page_size": 50}),
                "litsense": s.litsense.model_copy(
                    update={"query_style": "natural" if natural_litsense else "keywords"}
                ),
                "rank_for_values": True,
                "merge_strategy": "global",
                "population_filter": True,
                "ladder_version": "v2",
                "fulltext_excerpts": True,
                "llm_rerank": llm_rerank,
            }
        )

    return update


def _with(base: Callable[[Settings], Settings], **update: Any) -> Callable[[Settings], Settings]:
    return lambda s: base(s).model_copy(update=update)


CONFIGS: dict[str, RunConfig] = {
    c.name: c
    for c in (
        RunConfig(
            "current",
            "Europe PMC + LitSense passages, relaxation ladders, lexical rerank (the original "
            "method)",
            _original("europe_pmc", "litsense"),
        ),
        RunConfig(
            "current_fixed",
            "current method, unchanged except that Europe PMC replies without results are "
            "retried (they made Europe PMC drop out on 11 of 50 questions in the `current` run)",
            _original("europe_pmc", "litsense"),
        ),
        RunConfig(
            "openrouter_search",
            "OpenRouter web search server tool (Exa, 8 results, medical domains), lexical rerank",
            _original("openrouter_search"),
        ),
        RunConfig(
            "improved_1to4",
            "changes 1-4: value-first ranking in one list across sources, 50 Europe PMC "
            "candidates, animal/age filter, article-body search with excerpts, value-based "
            "broadening without the unhelpful rungs (medsim's default since they were measured)",
            _improved(),
        ),
        RunConfig(
            "improved_1to5",
            "changes 1-5: improved_1to4 plus natural-language LitSense queries",
            _improved(natural_litsense=True),
        ),
        RunConfig(
            "improved_1to6",
            "changes 1-6: improved_1to5 plus an LLM (the default model) picking the 8 "
            "documents from the best 20",
            _improved(natural_litsense=True, llm_rerank=True),
        ),
        RunConfig(
            "openrouter_search_improved",
            "OpenRouter web search with changes 1-3 applied: 10 results (same $0.007 fee), "
            "3,000-character excerpts, value-first ranking, population filter, excerpts around "
            "the variable from Europe PMC full text of PMC hits",
            lambda s: _original("openrouter_search")(s).model_copy(
                update={
                    "openrouter_search": s.openrouter_search.model_copy(
                        update={"max_results": 10, "max_characters": 3000}
                    ),
                    "rank_for_values": True,
                    "merge_strategy": "global",
                    "population_filter": True,
                    "fulltext_excerpts": True,
                }
            ),
        ),
        RunConfig(
            "sentences",
            "as current, LitSense in sentence mode",
            lambda s: _original("europe_pmc", "litsense")(s).model_copy(
                update={"litsense": s.litsense.model_copy(update={"mode": "sentences"})}
            ),
        ),
        RunConfig(
            "no_rerank",
            "as current, without the lexical rerank",
            _with(_original("europe_pmc", "litsense"), rerank_documents=False),
        ),
        RunConfig(
            "reference_only",
            "as current, but searching reference ranges instead of the diagnosis",
            _original("europe_pmc", "litsense"),
            condition_blind=True,
        ),
    )
}


# --- retrieval wrappers -------------------------------------------------------------------------


def _norm_pmcid(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    return text if text.startswith("PMC") else f"PMC{text}"


def document_ids(doc: RetrievedDocument) -> tuple[str | None, str | None]:
    """(pmid, pmcid) from the source record, falling back to the URL."""
    raw = doc.raw
    pmid = str(raw["pmid"]).strip() if raw.get("pmid") else None
    pmcid = _norm_pmcid(raw.get("pmcid"))
    if (pmid is None or pmcid is None) and doc.url:
        url_pmid, url_pmcid = identifiers_from_url(doc.url)
        pmid, pmcid = pmid or url_pmid, pmcid or url_pmcid
    return pmid, pmcid


class SourceArticleFilter:
    """Retriever wrapper that drops the case's own source article from every result list."""

    def __init__(self, inner: Retriever, *, pmcid: str | None, pmid: str | None) -> None:
        self.name = inner.name
        self._inner = inner
        self._pmcid = _norm_pmcid(pmcid)
        self._pmid = pmid
        self.excluded: list[str] = []

    def _is_source(self, doc: RetrievedDocument) -> bool:
        pmid, pmcid = document_ids(doc)
        return bool((self._pmcid and pmcid == self._pmcid) or (self._pmid and pmid == self._pmid))

    def search(self, query: str, **params: Any) -> list[RetrievedDocument]:
        kept = []
        for doc in self._inner.search(query, **params):
            if self._is_source(doc):
                if doc.doc_id not in self.excluded:  # every ladder rung can return it again
                    self.excluded.append(doc.doc_id)
            else:
                kept.append(doc)
        return kept

    def parameters(self) -> dict[str, Any]:
        return self._inner.parameters() | {
            "source_article_filter": {"pmcid": self._pmcid, "pmid": self._pmid,
                                      "excluded": len(self.excluded)}
        }  # fmt: skip


def condition_blind(lq: LiteratureQuery) -> LiteratureQuery:
    """Replace the diagnosis with reference-range terms: a baseline that ignores the disease."""
    if not lq.variable_terms:
        return lq
    return lq.model_copy(
        update={
            "keywords": f"{lq.variable_terms[0]} reference range healthy adults",
            "condition_terms": list(REFERENCE_TERMS),
            "related_condition_terms": [],
            "context_terms": [],
        }
    )


class ConditionBlindAggregator(RetrievalAggregator):
    def search(
        self, query: LiteratureQuery | str, *, records: list[LLMCallRecord] | None = None
    ) -> tuple[LiteratureSearchResult, dict[str, Any]]:
        blind = condition_blind(query) if isinstance(query, LiteratureQuery) else query
        return super().search(blind, records=records)


class LiveRetrievers:
    """Builds fresh retrievers per question (they keep per-search state) that share one HTTP
    client, one cache, and one LitSense rate limiter (1 request/s across all workers)."""

    def __init__(self, settings: Settings, *, cache: bool = True) -> None:
        self._http = httpx.Client()
        self._cache = ResponseCache(settings.cache_dir) if cache else None
        self._litsense_rate = RateLimiter(settings.litsense.min_interval_s)
        self._user_agent = settings.user_agent()

    def __call__(self, settings: Settings) -> list[Retriever]:
        retrievers: list[Retriever] = []
        for name in dict.fromkeys(settings.enabled_sources):
            if name == "europe_pmc":
                retrievers.append(EuropePMCRetriever(
                    settings.europe_pmc, user_agent=self._user_agent, http_client=self._http,
                    cache=self._cache,
                ))  # fmt: skip
            elif name == "litsense":
                retrievers.append(LitSenseRetriever(
                    settings.litsense, user_agent=self._user_agent, http_client=self._http,
                    cache=self._cache, rate_limiter=self._litsense_rate,
                ))  # fmt: skip
            elif name == "openrouter_search":
                retrievers.append(OpenRouterSearchRetriever.from_settings(
                    settings, cache=self._cache, http_client=self._http
                ))  # fmt: skip
        return retrievers

    def fulltext(self, settings: Settings) -> FullTextFetcher:
        return FullTextFetcher.from_settings(settings, http_client=self._http, cache=self._cache)

    def lookup_pmid(self, settings: Settings, pmcid: str) -> str | None:
        """The PMID of a PMC article, via a Europe PMC ``PMCID:`` search."""
        cfg = settings.europe_pmc.model_copy(update={"page_size": 5, "result_type": "lite"})
        retriever = EuropePMCRetriever(
            cfg, user_agent=self._user_agent, http_client=self._http, cache=self._cache
        )
        for doc in retriever.search(f"PMCID:{pmcid}"):
            if _norm_pmcid(doc.raw.get("pmcid")) == _norm_pmcid(pmcid) and doc.raw.get("pmid"):
                return str(doc.raw["pmid"])
        return None

    def close(self) -> None:
        self._http.close()


# --- one question -------------------------------------------------------------------------------


def _doc_record(rank: int, doc: RetrievedDocument) -> DocRecord:
    raw = doc.raw
    pmid, pmcid = document_ids(doc)
    if doc.source == "europe_pmc":
        full = strip_html(raw.get("abstractText"))
        journal_info = raw.get("journalInfo") or {}
        journal = (journal_info.get("journal") or {}).get("title") or raw.get("journalTitle")
        pub_types = (raw.get("pubTypeList") or {}).get("pubType") or []
        pub_types = [pub_types] if isinstance(pub_types, str) else list(pub_types)
        pub_year = raw.get("pubYear")
    else:
        full = str(raw.get("text") or raw.get("content") or "").strip()
        journal, pub_types, pub_year = None, [], None
    truncated = doc.text.endswith("…") and len(full) > len(doc.text)
    return DocRecord(
        rank=rank, source=doc.source, doc_id=doc.doc_id, title=doc.title, text=doc.text,
        full_text=full if truncated else None, url=doc.url, pmid=pmid, pmcid=pmcid,
        journal=str(journal) if journal else None, pub_year=str(pub_year) if pub_year else None,
        pub_types=[str(t) for t in pub_types],
    )  # fmt: skip


def record_from_response(
    item: Item,
    config: str,
    response: EnvironmentResponse,
    env: MedicalEnvironment,
    excluded: list[str],
    started_at: str,
    wall_time_s: float,
) -> RunRecord:
    params = response.retriever_parameters
    result = response.literature_search_result
    attempts = {
        source: list(info.get("query_attempts", []))
        for source, info in (params.get("per_source") or {}).items()
    }
    retrieval_cost = sum(
        float(a.get("cost_usd") or 0.0) for source in attempts.values() for a in source
    )
    stage_cost: dict[str, float] = {}
    for call in response.llm_calls:
        if call.stage in RETRIEVAL_STAGES:
            retrieval_cost += call.cost_usd or 0.0
        else:
            stage_cost[call.stage] = stage_cost.get(call.stage, 0.0) + (call.cost_usd or 0.0)
    fact = next(
        (f for f in env.ledger.facts_for(item.case.case_id) if f.answer_source == "literature"),
        None,
    )
    return RunRecord(
        item_id=item.item_id, config=config, question_set=item.question_set, status="ok",
        started_at=started_at, wall_time_s=round(wall_time_s, 2), path=params.get("path"),
        answer_source=response.answer_source, output_answer=response.output_answer,
        confidence=response.confidence, evidence=response.evidence,
        clinical_variable=fact.clinical_variable if fact else None,
        answer_value=fact.value if fact else None, answer_unit=fact.unit if fact else None,
        literature_query=result.query if result else None,
        documents=[_doc_record(i + 1, d) for i, d in enumerate(result.documents if result else [])],
        excluded_source_docs=excluded, failed_sources=list(params.get("failed_sources") or []),
        source_errors=list(result.errors) if result else [], query_attempts=attempts,
        llm_calls=response.llm_calls, retrieval_cost_usd=round(retrieval_cost, 6),
        retrieval_notes={k: params[k] for k in RETRIEVAL_NOTES if k in params},
        llm_cost_usd={k: round(v, 6) for k, v in stage_cost.items()},
    )  # fmt: skip


def run_one(
    item: Item,
    config: RunConfig,
    *,
    llm: LLMClient,
    base_settings: Settings,
    retrievers: RetrieverFactory,
    fulltext: FullTextFactory | None = None,
) -> RunRecord:
    settings = config.settings(base_settings)
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    started = time.perf_counter()
    filters = [
        SourceArticleFilter(r, pmcid=item.source_pmcid, pmid=item.source_pmid)
        for r in retrievers(settings)
    ]
    aggregator = build_aggregator(
        settings,
        filters,
        llm,
        aggregator_cls=ConditionBlindAggregator if config.condition_blind else RetrievalAggregator,
        fulltext=fulltext(settings) if fulltext and settings.fulltext_excerpts else None,
    )
    env = MedicalEnvironment(
        case_study=item.case, llm=llm, retrievers=filters, settings=settings, aggregator=aggregator
    )

    def excluded() -> list[str]:
        return [doc_id for f in filters for doc_id in f.excluded]

    try:
        response = env.query(item.question)
    except MedSimError as exc:
        return RunRecord(
            item_id=item.item_id, config=config.name, question_set=item.question_set,
            status="error", error=f"{type(exc).__name__}: {exc}"[:500], started_at=started_at,
            wall_time_s=round(time.perf_counter() - started, 2), excluded_source_docs=excluded(),
        )  # fmt: skip
    return record_from_response(
        item, config.name, response, env, excluded(), started_at, time.perf_counter() - started
    )


def run_configs(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[RunConfig],
    *,
    llm: LLMClient,
    base_settings: Settings,
    retrievers: RetrieverFactory,
    fulltext: FullTextFactory | None = None,
    workers: int = 4,
) -> dict[str, dict[str, Any]]:
    """Run every (config, item) not yet answered successfully; errors are retried on rerun.

    All configurations share one thread pool, so a slow question in one configuration does not
    hold back the others. Questions are interleaved across configurations so every
    configuration progresses (and a stopped run leaves comparable partial results).
    """
    writers = {c.name: JsonlWriter(ws.run_file(c.name)) for c in configs}
    counts: dict[str, Counter[str]] = {c.name: Counter() for c in configs}
    cost: dict[str, float] = {c.name: 0.0 for c in configs}
    todo: list[tuple[RunConfig, Item]] = []
    for config in configs:
        latest = latest_by(read_models(ws.run_file(config.name), RunRecord), lambda r: r.item_id)
        done = {key for key, r in latest.items() if r.status == "ok"}
        counts[config.name]["todo"] = sum(i.item_id not in done for i in items)
        todo += [(config, i) for i in items if i.item_id not in done]
    todo.sort(key=lambda pair: [i.item_id for i in items].index(pair[1].item_id))

    def work(pair: tuple[RunConfig, Item]) -> RunRecord:
        config, item = pair
        return run_one(
            item, config, llm=llm, base_settings=base_settings, retrievers=retrievers,
            fulltext=fulltext,
        )  # fmt: skip

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(work, pair) for pair in todo]
        for n, record in enumerate((f.result() for f in as_completed(futures)), 1):
            writers[record.config].write(record)
            counts[record.config][record.status] += 1
            counts[record.config][f"path:{record.path}"] += 1
            spent = record.retrieval_cost_usd + calls_cost(record.llm_calls)
            cost[record.config] += spent
            logger.info(
                "run %s %s: %s %s, %d docs, %.1fs, $%.4f [%d/%d]",
                record.config, record.item_id, record.status, record.path or record.error,
                len(record.documents), record.wall_time_s, spent, n, len(todo),
            )  # fmt: skip
    elapsed = round(time.perf_counter() - started, 1)
    return {
        name: {**counts[name], "cost_usd": round(cost[name], 4), "elapsed_s": elapsed}
        for name in counts
    }
