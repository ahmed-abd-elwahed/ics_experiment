"""Fan out a query to all retrievers, relax per source if needed, rank, dedupe, merge.

With every option at its default this is the original method: per-source ladders broadened
while few documents mention the variable, a lexical rerank within each source, a round-robin
merge, and the first ``max_doc_chars`` of each document. The options are the retrieval changes
measured in results/README.md:

1. ``value_first`` + ``merge="global"``: documents stating a value rank first, in one list.
2. ``population_filter``: drop animal studies, rank other age groups lower.
3. ``ladder.version="v2"`` + ``excerpts``: search article bodies; keep the sentences about the
   variable (from open-access full text when ``fulltext`` is given) instead of the first chars.
4. ``ladder.version="v2"``: no rungs that never helped; broaden only while few documents state a
   value; related-condition results rank lower.
5. ``ladder.litsense_query="natural"``: a natural-language LitSense query.
6. ``reranker``: an LLM picks the final documents from the best ``rerank_candidates``.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Literal

from medsim.errors import MedSimError, RetrieverError
from medsim.models import (
    LiteratureQuery,
    LiteratureSearchResult,
    LLMCallRecord,
    RetrievedDocument,
)
from medsim.retrieval.base import Retriever
from medsim.retrieval.fulltext import FullTextFetcher
from medsim.retrieval.population import non_human
from medsim.retrieval.query_formulation import (
    V1,
    LadderOptions,
    RelevanceScorer,
    doc_key,
    excerpt,
    query_ladder,
)
from medsim.retrieval.rerank import LLMReranker

logger = logging.getLogger("medsim.retrieval")

_NON_WORD = re.compile(r"\W+")


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_NON_WORD.sub(" ", text.lower()).split())


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _full_text_candidate(doc: RetrievedDocument) -> bool:
    """Whether Europe PMC may have the document's full text: open-access Europe PMC records,
    and PMC articles found by web search (not all are open access; a miss costs one request)."""
    if not doc.raw.get("pmcid"):
        return False
    if doc.source == "europe_pmc":
        return str(doc.raw.get("isOpenAccess", "")).upper() == "Y"
    return doc.source == "openrouter_search"


@dataclass
class _SourceOutcome:
    documents: list[RetrievedDocument]
    attempts: list[dict[str, Any]]
    parameters: dict[str, Any]
    error: str | None
    levels: dict[str, str] = field(default_factory=dict)  # doc key -> rung that found it


class RetrievalAggregator:
    def __init__(
        self,
        retrievers: Sequence[Retriever],
        *,
        max_documents: int,
        max_doc_chars: int,
        near_duplicate_threshold: float = 0.9,
        rerank: bool = True,
        relax_min_relevant: int = 3,
        value_first: bool = False,
        merge: Literal["round_robin", "global"] = "round_robin",
        population_filter: bool = False,
        ladder: LadderOptions = V1,
        excerpts: bool = False,
        fulltext: FullTextFetcher | None = None,
        fulltext_max_docs: int = 10,
        reranker: LLMReranker | None = None,
        rerank_candidates: int = 20,
    ) -> None:
        if not retrievers:
            raise ValueError("RetrievalAggregator requires at least one retriever")
        self.retrievers = list(retrievers)
        self.max_documents = max_documents
        self.max_doc_chars = max_doc_chars
        self.near_duplicate_threshold = near_duplicate_threshold
        self.rerank = rerank
        self.relax_min_relevant = relax_min_relevant
        self.value_first = value_first
        self.merge = merge
        self.population_filter = population_filter
        self.ladder = ladder
        self.excerpts = excerpts
        self.fulltext = fulltext
        self.fulltext_max_docs = fulltext_max_docs
        self.reranker = reranker
        self.rerank_candidates = rerank_candidates

    def _ranking_label(self) -> str:
        if not self.rerank:
            return "round-robin interleave; source-native order within each source"
        within = "lexical term rerank within each source" + (
            " (value first)" if self.value_first else ""
        )
        merge = (
            "one ranked list across sources" if self.merge == "global" else "round-robin interleave"
        )
        return f"{within}, then {merge}"

    def configured_parameters(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "sources": [r.name for r in self.retrievers],
            "max_documents": self.max_documents,
            "max_doc_chars": self.max_doc_chars,
            "dedupe": {
                "by_identifier": True,
                "near_duplicate_text_jaccard": self.near_duplicate_threshold,
            },
            "query_formulation": {
                "strategy": "source-specific relaxation ladder",
                "ladder_version": self.ladder.version,
                "litsense_query": self.ladder.litsense_query,
                "relax_until_relevant_docs": self.relax_min_relevant,
                "relax_counts": "documents stating a value"
                if self.ladder.version == "v2"
                else "documents mentioning the variable",
            },
            "ranking": self._ranking_label(),
            "population_filter": self.population_filter,
            "excerpt_mode": (
                ("full text (open access) or abstract windows" if self.fulltext else "windows")
                if self.excerpts
                else "first max_doc_chars characters"
            ),
        }
        if self.reranker is not None:
            params["llm_rerank"] = {
                "model": self.reranker.model,
                "candidates": self.rerank_candidates,
            }
        return params

    def search(
        self, query: LiteratureQuery | str, *, records: list[LLMCallRecord] | None = None
    ) -> tuple[LiteratureSearchResult, dict[str, Any]]:
        """Return the merged result plus the parameters actually used for this call.

        A plain string is sent unchanged to every source (no relaxation, no reranking). LLM
        calls made while selecting documents (``reranker``) are appended to ``records``.
        """
        started = time.perf_counter()
        lq = query if isinstance(query, LiteratureQuery) else LiteratureQuery(keywords=query)
        scorer = RelevanceScorer(
            lq,
            value_first=self.value_first,
            age_penalty=self.population_filter,
            related_penalty=self.ladder.version == "v2",
        )

        with ThreadPoolExecutor(max_workers=len(self.retrievers)) as pool:
            futures = [
                (r, pool.submit(self._search_source, r, lq, scorer)) for r in self.retrievers
            ]
            outcomes = {retriever.name: future.result() for retriever, future in futures}

        errors = [o.error for o in outcomes.values() if o.error]
        failed = [name for name, o in outcomes.items() if o.error and not o.documents]
        levels = {k: v for o in outcomes.values() for k, v in o.levels.items()}
        extra: dict[str, Any] = {}

        per_source_docs: dict[str, list[RetrievedDocument]] = {}
        dropped: dict[str, int] = {}
        for name, o in outcomes.items():
            if name in failed:
                continue
            docs = o.documents
            if self.population_filter:
                kept = [d for d in docs if not non_human(d)]
                dropped[name] = len(docs) - len(kept)
                docs = kept
            per_source_docs[name] = docs
        if self.population_filter:
            extra["population_filtered"] = dropped
            extra["patient_age_group"] = lq.patient_age_group
        if self.excerpts and scorer.active:
            per_source_docs, extra["excerpts"] = self._excerpt(per_source_docs, scorer, levels)
        if self.rerank and scorer.active:
            per_source_docs = {n: scorer.rank(d, levels) for n, d in per_source_docs.items()}

        limit = self.max_documents
        if self.reranker is not None and scorer.active:
            limit = max(self.rerank_candidates, self.max_documents)
        if self.merge == "global" and self.rerank and scorer.active:
            documents = self._merge_global(per_source_docs, scorer, levels, limit)
        else:
            documents = self._merge(per_source_docs, limit)
        if self.reranker is not None and scorer.active and documents:
            documents, extra["llm_rerank"] = self._llm_select(lq, documents, records)

        counts = {r.name: 0 for r in self.retrievers}
        for doc in documents:
            counts[doc.source] = counts.get(doc.source, 0) + 1

        result = LiteratureSearchResult(
            query=self._sent_query_label(outcomes, lq),
            documents=documents,
            per_source_counts=counts,
            errors=errors,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        params = (
            self.configured_parameters()
            | {
                "per_source": {
                    name: o.parameters | {"query_attempts": o.attempts}
                    for name, o in outcomes.items()
                },
                "raw_counts": {name: len(docs) for name, docs in per_source_docs.items()},
                "failed_sources": failed,
            }
            | extra
        )
        return result, params

    def _search_source(
        self, retriever: Retriever, lq: LiteratureQuery, scorer: RelevanceScorer
    ) -> _SourceOutcome:
        """Walk the source's ladder, accumulating unique documents, until enough are relevant.

        v1 counts documents mentioning the variable; v2 counts documents stating a value, and
        counts article-body hits too: they mention the variable in a case description, results
        section, or table, where the value is (their full text is read later).
        """
        collected: list[RetrievedDocument] = []
        levels: dict[str, str] = {}
        attempts: list[dict[str, Any]] = []
        error: str | None = None
        v2 = self.ladder.version == "v2"

        for attempt in query_ladder(retriever.name, lq, self.ladder):
            try:
                docs = retriever.search(attempt.query)
            except RetrieverError as exc:
                error = str(exc)
            except Exception as exc:  # a broken source must not sink the others
                logger.exception("retriever %s raised unexpectedly", retriever.name)
                error = f"{retriever.name}: unexpected {type(exc).__name__}: {exc}"
            if error is not None:
                attempts.append({"level": attempt.level, "query": attempt.query, "error": error})
                break

            added = 0
            for doc in docs:
                key = doc_key(doc)
                if key not in levels:
                    levels[key] = attempt.level
                    collected.append(doc)
                    added += 1
            relevant = sum(
                1
                for doc in collected
                if (v2 and (scorer.has_value(doc) or levels[doc_key(doc)].startswith("body_")))
                or (not v2 and scorer.mentions_variable(doc))
            )
            entry: dict[str, Any] = {
                "level": attempt.level,
                "query": attempt.query,
                "returned": len(docs),
                "new": added,
                "relevant_total": relevant,
            }
            cost = retriever.parameters().get("cost_usd")  # paid sources report their fee
            if isinstance(cost, int | float):
                entry["cost_usd"] = cost
            attempts.append(entry)
            if relevant >= self.relax_min_relevant:
                break

        return _SourceOutcome(collected, attempts, retriever.parameters(), error, levels)

    def _excerpt(
        self,
        per_source: dict[str, list[RetrievedDocument]],
        scorer: RelevanceScorer,
        levels: dict[str, str],
    ) -> tuple[dict[str, list[RetrievedDocument]], dict[str, int]]:
        """Replace long texts with the sentences about the variable.

        Open-access Europe PMC candidates and PMC pages found by web search are excerpted from
        their full text (their own text included): article-body hits first, then the
        best-ranked others, up to ``fulltext_max_docs``. Other long texts are excerpted from
        their own text; short texts stay as they are.
        """
        full: dict[str, list[str]] = {}
        stats = {"full_text_fetched": 0, "full_text_used": 0, "windows": 0}
        if self.fulltext is not None and self.fulltext_max_docs > 0:
            candidates = [d for docs in per_source.values() for d in docs]
            open_access = [d for d in scorer.rank(candidates, levels) if _full_text_candidate(d)]
            body_first = sorted(
                open_access, key=lambda d: not levels.get(doc_key(d), "").startswith("body_")
            )
            targets = body_first[: self.fulltext_max_docs]
            fetcher = self.fulltext
            with ThreadPoolExecutor(max_workers=4) as pool:
                bodies = list(pool.map(lambda d: fetcher.blocks(str(d.raw["pmcid"])), targets))
            for doc, body in zip(targets, bodies, strict=True):
                if body:
                    full[doc_key(doc)] = [doc.text, *body]
            stats["full_text_fetched"] = len(full)

        out: dict[str, list[RetrievedDocument]] = {}
        for name, docs in per_source.items():
            updated = []
            for doc in docs:
                text: str | None = None
                origin = ""
                if doc_key(doc) in full:
                    text = excerpt(full[doc_key(doc)], scorer, self.max_doc_chars)
                    origin = "full_text"
                if text is None and len(doc.text) > self.max_doc_chars:
                    text = excerpt([doc.text], scorer, self.max_doc_chars)
                    origin = "window"
                if text is None:
                    updated.append(doc)
                    continue
                stats["full_text_used" if origin == "full_text" else "windows"] += 1
                updated.append(
                    doc.model_copy(update={"text": text, "raw": {**doc.raw, "excerpt": origin}})
                )
            out[name] = updated
        return out, stats

    def _llm_select(
        self,
        lq: LiteratureQuery,
        candidates: list[RetrievedDocument],
        records: list[LLMCallRecord] | None,
    ) -> tuple[list[RetrievedDocument], dict[str, Any]]:
        """The LLM's picks first, then the lexical order, capped at ``max_documents``.

        An LLM failure keeps the lexical order: selection must never lose a search result.
        """
        assert self.reranker is not None
        calls: list[LLMCallRecord] = [] if records is None else records
        try:
            chosen = self.reranker.select(lq, candidates, records=calls)
        except MedSimError as exc:
            logger.warning("LLM rerank failed, keeping lexical order: %s", exc)
            return candidates[: self.max_documents], {"error": str(exc)[:200]}
        order = chosen + [i for i in range(len(candidates)) if i not in chosen]
        selected = [candidates[i] for i in order[: self.max_documents]]
        return selected, {"candidates": len(candidates), "selected": len(chosen)}

    @staticmethod
    def _sent_query_label(outcomes: dict[str, _SourceOutcome], lq: LiteratureQuery) -> str:
        """The query each source was last sent; a single string when all sources agree."""
        final: dict[str, str] = {
            name: str(o.attempts[-1]["query"]) for name, o in outcomes.items() if o.attempts
        }
        if not final:
            return lq.keywords
        distinct = set(final.values())
        if len(distinct) == 1:
            return distinct.pop()
        return " | ".join(f"{name}: {query}" for name, query in final.items())

    def _merge(
        self, per_source: dict[str, list[RetrievedDocument]], limit: int
    ) -> list[RetrievedDocument]:
        """Round-robin across sources, each in its own order."""
        queues = [list(per_source.get(r.name, [])) for r in self.retrievers]
        kept: list[RetrievedDocument] = []
        seen_ids: set[str] = set()
        seen_tokens: list[frozenset[str]] = []

        while len(kept) < limit and any(queues):
            for queue in queues:
                if len(kept) >= limit:
                    break
                while queue:
                    doc = queue.pop(0)
                    if self._accept(doc, seen_ids, seen_tokens):
                        kept.append(self._truncate(doc))
                        break
        return kept

    def _merge_global(
        self,
        per_source: dict[str, list[RetrievedDocument]],
        scorer: RelevanceScorer,
        levels: dict[str, str],
        limit: int,
    ) -> list[RetrievedDocument]:
        """One list ranked by score across sources; equal scores alternate between sources."""
        entries = []
        for source_index, retriever in enumerate(self.retrievers):
            for rank, doc in enumerate(per_source.get(retriever.name, [])):
                score = scorer.score(doc, levels.get(doc_key(doc)))
                entries.append((-score, rank, source_index, doc))
        entries.sort(key=lambda e: (e[0], e[1], e[2]))
        kept: list[RetrievedDocument] = []
        seen_ids: set[str] = set()
        seen_tokens: list[frozenset[str]] = []
        for *_, doc in entries:
            if len(kept) >= limit:
                break
            if self._accept(doc, seen_ids, seen_tokens):
                kept.append(self._truncate(doc))
        return kept

    def _accept(
        self, doc: RetrievedDocument, seen_ids: set[str], seen_tokens: list[frozenset[str]]
    ) -> bool:
        key = doc_key(doc)
        tokens = _tokens(doc.text)
        if not tokens or key in seen_ids:
            return False
        if any(_jaccard(tokens, other) >= self.near_duplicate_threshold for other in seen_tokens):
            return False
        seen_ids.add(key)
        seen_tokens.append(tokens)
        return True

    def _truncate(self, doc: RetrievedDocument) -> RetrievedDocument:
        if len(doc.text) <= self.max_doc_chars:
            return doc
        return doc.model_copy(update={"text": doc.text[: self.max_doc_chars - 1].rstrip() + "…"})
