"""MedicalEnvironment: orchestrates ledger -> Stage A -> Stage B -> retrieval -> Stage C."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from medsim import rules
from medsim.case_study import load_case_study
from medsim.config import Settings, load_settings
from medsim.errors import ConfigError
from medsim.ledger import FactLedger
from medsim.llm.base import LLMClient
from medsim.llm.openrouter import OpenRouterClient
from medsim.models import (
    AnswerSource,
    CaseStudy,
    Confidence,
    EnvironmentResponse,
    LedgerFact,
    LiteratureSearchResult,
    LLMCallRecord,
    RetrievedDocument,
)
from medsim.retrieval.aggregator import RetrievalAggregator
from medsim.retrieval.base import Retriever
from medsim.retrieval.cache import ResponseCache
from medsim.retrieval.europe_pmc import EuropePMCRetriever
from medsim.retrieval.fulltext import FullTextFetcher
from medsim.retrieval.litsense import LitSenseRetriever
from medsim.retrieval.openrouter_search import OpenRouterSearchRetriever
from medsim.retrieval.query_formulation import LadderOptions, to_literature_query
from medsim.retrieval.rerank import LLMReranker
from medsim.stages.query_builder import QueryBuilder
from medsim.stages.resolver import Resolver
from medsim.stages.synthesizer import Synthesizer

logger = logging.getLogger("medsim.environment")

OFF_TOPIC_ANSWER = "This environment only answers questions about the simulated patient."
WITHHELD_ANSWER = "That information is withheld in this simulation."
_CONFIDENCE_RANK: dict[Confidence, int] = {"low": 0, "medium": 1, "high": 2}


@dataclass
class _Outcome:
    query: str
    path: str
    answer: str
    answer_source: AnswerSource
    confidence: Confidence
    evidence: list[str] = field(default_factory=list)
    literature_search: bool = False
    literature_query: str | None = None
    result: LiteratureSearchResult | None = None
    retrieval_params: dict[str, Any] = field(default_factory=dict)
    llm_calls: list[LLMCallRecord] = field(default_factory=list)


def build_retrievers(settings: Settings) -> list[Retriever]:
    cache = ResponseCache(settings.cache_dir) if settings.cache_enabled else None
    user_agent = settings.user_agent()
    retrievers: list[Retriever] = []
    for name in dict.fromkeys(settings.enabled_sources):
        if name == "europe_pmc" and settings.europe_pmc.enabled:
            retrievers.append(
                EuropePMCRetriever(settings.europe_pmc, user_agent=user_agent, cache=cache)
            )
        elif name == "litsense" and settings.litsense.enabled:
            retrievers.append(
                LitSenseRetriever(settings.litsense, user_agent=user_agent, cache=cache)
            )
        elif name == "openrouter_search" and settings.openrouter_search.enabled:
            retrievers.append(OpenRouterSearchRetriever.from_settings(settings, cache=cache))
    if not retrievers:
        raise ConfigError("No literature sources enabled; set MEDSIM_ENABLED_SOURCES.")
    if not settings.contact_email:
        logger.warning("MEDSIM_CONTACT_EMAIL is unset; User-Agent will carry no contact address.")
    return retrievers


def build_aggregator(
    settings: Settings,
    retrievers: Sequence[Retriever],
    llm: LLMClient,
    *,
    aggregator_cls: type[RetrievalAggregator] = RetrievalAggregator,
    fulltext: FullTextFetcher | None = None,
) -> RetrievalAggregator:
    """The aggregator the settings describe (see medsim/retrieval/aggregator.py for options)."""
    if settings.fulltext_excerpts and fulltext is None and settings.fulltext_max_docs > 0:
        fulltext = FullTextFetcher.from_settings(settings)
    reranker = None
    if settings.llm_rerank:
        reranker = LLMReranker(
            llm, model=settings.model_for("reranker"), max_tokens=settings.reranker_max_tokens
        )
    return aggregator_cls(
        retrievers,
        max_documents=settings.max_documents,
        max_doc_chars=settings.max_doc_chars,
        near_duplicate_threshold=settings.near_duplicate_threshold,
        rerank=settings.rerank_documents,
        relax_min_relevant=settings.relax_min_relevant,
        value_first=settings.rank_for_values,
        merge=settings.merge_strategy,
        population_filter=settings.population_filter,
        ladder=LadderOptions(settings.ladder_version, settings.litsense.query_style),
        excerpts=settings.fulltext_excerpts,
        fulltext=fulltext if settings.fulltext_excerpts else None,
        fulltext_max_docs=settings.fulltext_max_docs,
        reranker=reranker,
        rerank_candidates=settings.rerank_candidates,
    )


def case_text(case: CaseStudy) -> str:
    return " ".join([case.narrative, *case.structured_findings.values()])


class MedicalEnvironment:
    def __init__(
        self,
        case_study: CaseStudy,
        llm: LLMClient,
        retrievers: Sequence[Retriever],
        settings: Settings,
        *,
        ledger: FactLedger | None = None,
        resolver: Resolver | None = None,
        query_builder: QueryBuilder | None = None,
        synthesizer: Synthesizer | None = None,
        aggregator: RetrievalAggregator | None = None,
    ) -> None:
        if aggregator is None and not retrievers:
            raise ConfigError("MedicalEnvironment needs at least one retriever.")
        self.case_study = case_study
        self.llm = llm
        self.settings = settings
        self.ledger = ledger or FactLedger()
        self.resolver = resolver or Resolver(
            llm, model=settings.model_for("resolver"), max_tokens=settings.resolver_max_tokens
        )
        self.query_builder = query_builder or QueryBuilder(
            llm,
            model=settings.model_for("query_builder"),
            max_tokens=settings.query_builder_max_tokens,
        )
        self.synthesizer = synthesizer or Synthesizer(
            llm,
            model=settings.model_for("synthesizer"),
            max_tokens=settings.synthesizer_max_tokens,
            temperature=settings.synthesizer_temperature,
        )
        self.aggregator = aggregator or build_aggregator(settings, retrievers, llm)
        self._age_group = rules.age_group(case_text(case_study))

    @classmethod
    def from_case_file(
        cls,
        path: str | Path,
        *,
        settings: Settings | None = None,
        verify_models: bool | None = None,
    ) -> MedicalEnvironment:
        settings = settings or load_settings()
        case = load_case_study(path)
        llm = OpenRouterClient(settings)
        if settings.verify_models_on_startup if verify_models is None else verify_models:
            llm.verify_models()
        return cls(
            case_study=case, llm=llm, retrievers=build_retrievers(settings), settings=settings
        )

    def reset(self) -> None:
        """Clear this case's ledger facts; facts for other cases in a shared ledger are kept."""
        self.ledger.reset(self.case_study.case_id)

    def close(self) -> None:
        close = getattr(self.llm, "close", None)
        if callable(close):
            close()

    # -- public entry point ---------------------------------------------------------------------

    def query(self, query: str) -> EnvironmentResponse:
        text = query.strip()
        if not text:
            outcome = _Outcome(
                query=query, path="empty_query", answer="Empty question.",
                answer_source="unanswerable", confidence="low",
            )  # fmt: skip
            return self._build_response(query, [outcome])
        sub_queries = rules.split_multipart(text)
        outcomes = [self._answer_single(sub) for sub in sub_queries]
        return self._build_response(text, outcomes)

    # -- single-question pipeline ---------------------------------------------------------------

    def _answer_single(self, query: str) -> _Outcome:
        records: list[LLMCallRecord] = []
        case_id = self.case_study.case_id

        use_ledger = self.settings.ledger_enabled
        fact = self.ledger.lookup(query, case_id=case_id) if use_ledger else None
        if fact is not None:
            return self._from_ledger(query, fact, records, path="ledger_hit")

        established = self.ledger.prompt_block(case_id) if use_ledger else "(none)"
        resolved = self.resolver.run(
            query, self.case_study, established_facts=established, records=records
        )
        if resolved.query_scope == "off_topic":
            return self._unanswerable(query, "off_topic", OFF_TOPIC_ANSWER, records)
        if resolved.query_scope == "withheld":
            return self._unanswerable(query, "withheld", WITHHELD_ANSWER, records)
        if resolved.answerable_from_case and resolved.answer:
            if use_ledger:
                self.ledger.record(
                    case_id=case_id,
                    query=query, answer=resolved.answer, answer_source="case_study",
                    evidence=resolved.evidence_spans, confidence="high",
                )  # fmt: skip
            return _Outcome(
                query=query, path="case_study", answer=resolved.answer,
                answer_source="case_study", confidence="high",
                evidence=list(resolved.evidence_spans), llm_calls=records,
            )  # fmt: skip

        built = self.query_builder.run(
            query, self.case_study, partial_facts=resolved.partial_facts, records=records
        )
        if built.literature_query is None:
            reason = built.decline_reason or "the question has no meaningful literature answer"
            return self._unanswerable(
                query, "query_builder_declined", f"This cannot be answered: {reason}.", records
            )

        if use_ledger:
            fact = self.ledger.lookup(query, built.clinical_variable, case_id=case_id)
        if fact is not None:
            return self._from_ledger(query, fact, records, path="ledger_hit_after_query_builder")

        lq = to_literature_query(built).model_copy(update={"patient_age_group": self._age_group})
        result, params = self.aggregator.search(lq, records=records)
        retrieval = {"literature_query": built.literature_query, **params}
        base: dict[str, Any] = {
            "literature_search": True, "literature_query": built.literature_query,
            "result": result, "retrieval_params": retrieval,
        }  # fmt: skip

        if len(params["failed_sources"]) == len(self.aggregator.retrievers):
            return self._unanswerable(
                query, "all_sources_failed",
                "Literature sources are unavailable, so this cannot be answered.", records, **base,
            )  # fmt: skip
        if not result.documents:
            return self._unanswerable(
                query, "no_documents",
                "No relevant literature was found, so this cannot be answered.", records, **base,
            )  # fmt: skip

        synth_kwargs: dict[str, Any] = {
            "established_facts": established,
            "partial_facts": resolved.partial_facts,
            "clinical_variable": built.clinical_variable,
            "expected_answer_type": built.expected_answer_type,
            "records": records,
        }
        synthesized = self.synthesizer.run(query, self.case_study, result.documents, **synth_kwargs)
        if not synthesized.unanswerable and not synthesized.consistent_with_case:
            conflict = (
                synthesized.conflict or "the answer was flagged as inconsistent with the case"
            )
            synthesized = self.synthesizer.run(
                query, self.case_study, result.documents, conflict=conflict, **synth_kwargs
            )
            if not synthesized.unanswerable and not synthesized.consistent_with_case:
                detail = synthesized.conflict or conflict
                return self._unanswerable(
                    query, "inconsistent_with_case",
                    f"No answer consistent with the case study could be synthesized ({detail}).",
                    records, **base,
                )  # fmt: skip
        if synthesized.unanswerable:
            answer = synthesized.answer.strip() or "The literature does not support an answer."
            return self._unanswerable(query, "synthesizer_unanswerable", answer, records, **base)

        evidence = list(synthesized.supporting_doc_ids)
        if synthesized.literature_range:
            evidence.append(f"literature range: {synthesized.literature_range}")
        confidence: Confidence = synthesized.confidence if synthesized.supporting_doc_ids else "low"
        if use_ledger:
            self.ledger.record(
                case_id=case_id,
                query=query, answer=synthesized.answer, answer_source="literature",
                clinical_variable=built.clinical_variable, value=synthesized.value,
                unit=synthesized.unit, source_doc_ids=synthesized.supporting_doc_ids,
                evidence=evidence, confidence=confidence,
            )  # fmt: skip
        return _Outcome(
            query=query, path="literature", answer=synthesized.answer,
            answer_source="literature", confidence=confidence, evidence=evidence,
            llm_calls=records, **base,
        )  # fmt: skip

    def _from_ledger(
        self, query: str, fact: LedgerFact, records: list[LLMCallRecord], *, path: str
    ) -> _Outcome:
        return _Outcome(
            query=query,
            path=path,
            answer=self.ledger.render_answer(fact, query),
            answer_source=fact.answer_source,
            confidence=fact.confidence,
            evidence=[*fact.evidence, f"ledger:{fact.clinical_variable}"],
            retrieval_params={"ledger_key": fact.clinical_variable, "ledger_case_id": fact.case_id},
            llm_calls=records,
        )

    @staticmethod
    def _unanswerable(
        query: str, path: str, answer: str, records: list[LLMCallRecord], **extra: Any
    ) -> _Outcome:
        return _Outcome(
            query=query, path=path, answer=answer, answer_source="unanswerable",
            confidence="low", llm_calls=records, **extra,
        )  # fmt: skip

    # -- response assembly ----------------------------------------------------------------------

    def _build_response(self, input_query: str, outcomes: list[_Outcome]) -> EnvironmentResponse:
        multi = len(outcomes) > 1
        llm_calls = [call for o in outcomes for call in o.llm_calls]
        models = list(dict.fromkeys(call.model for call in llm_calls))
        used_llm = ", ".join(models) if models else self.settings.model_for("resolver")

        entries = [
            {
                "query": o.query,
                "path": o.path,
                "retrieval_performed": o.literature_search,
                **o.retrieval_params,
            }
            for o in outcomes
        ]
        if multi:
            retriever_parameters: dict[str, Any] = {"multi_part": True, "sub_queries": entries}
            answer = "\n".join(o.answer for o in outcomes)
            evidence = [f"[{o.query}] {e}" for o in outcomes for e in o.evidence]
        else:
            retriever_parameters = {"multi_part": False, **entries[0]}
            answer = outcomes[0].answer
            evidence = list(outcomes[0].evidence)

        sources = {o.answer_source for o in outcomes}
        answer_source: AnswerSource = (
            "literature" if "literature" in sources
            else "case_study" if "case_study" in sources
            else "unanswerable"
        )  # fmt: skip
        confidence = min((o.confidence for o in outcomes), key=_CONFIDENCE_RANK.__getitem__)

        return EnvironmentResponse(
            input_query=input_query,
            output_answer=answer,
            literature_search=any(o.literature_search for o in outcomes),
            literature_search_result=self._merge_results([o.result for o in outcomes if o.result]),
            retriever_parameters=retriever_parameters,
            used_llm=used_llm,
            answer_source=answer_source,
            evidence=evidence,
            confidence=confidence,
            llm_calls=llm_calls,
        )

    @staticmethod
    def _merge_results(results: list[LiteratureSearchResult]) -> LiteratureSearchResult | None:
        if not results:
            return None
        if len(results) == 1:
            return results[0]
        documents: dict[str, RetrievedDocument] = {}
        counts: dict[str, int] = {}
        for result in results:
            for doc in result.documents:
                documents.setdefault(doc.doc_id, doc)
            for source, n in result.per_source_counts.items():
                counts[source] = counts.get(source, 0) + n
        return LiteratureSearchResult(
            query=" | ".join(r.query for r in results),
            documents=list(documents.values()),
            per_source_counts=counts,
            errors=[e for r in results for e in r.errors],
            latency_ms=sum(r.latency_ms for r in results),
        )
