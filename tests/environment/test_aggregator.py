from __future__ import annotations

from typing import Any

from medsim.errors import RetrieverError
from medsim.models import LiteratureQuery, RetrievedDocument, SourceName
from medsim.retrieval.aggregator import RetrievalAggregator
from medsim.retrieval.base import Retriever
from medsim.retrieval.query_formulation import query_ladder


def _doc(source: SourceName, doc_id: str, text: str) -> RetrievedDocument:
    return RetrievedDocument(
        source=source, doc_id=doc_id, title=None, text=text, url=None, score=None, raw={}
    )


class FakeRetriever:
    def __init__(self, name: str, docs: list[RetrievedDocument] | Exception) -> None:
        self.name = name
        self._docs = docs
        self.queries: list[str] = []

    def search(self, query: str, **params: Any) -> list[RetrievedDocument]:
        self.queries.append(query)
        if isinstance(self._docs, Exception):
            raise self._docs
        return list(self._docs)

    def parameters(self) -> dict[str, Any]:
        return {"endpoint": f"https://{self.name}.test", "fake": True}


def _agg(
    *retrievers: Retriever, max_documents: int = 10, max_doc_chars: int = 1000
) -> RetrievalAggregator:
    return RetrievalAggregator(
        list(retrievers), max_documents=max_documents, max_doc_chars=max_doc_chars
    )


EPMC = [
    _doc("europe_pmc", f"PMID:{i}", f"europe pmc abstract number {i} about fever") for i in range(5)
]
LS = [
    _doc("litsense", f"PMID:{100 + i}#S-{i}", f"litsense passage {i} on temperature")
    for i in range(5)
]


def test_round_robin_interleaves_sources_and_caps() -> None:
    epmc, ls = FakeRetriever("europe_pmc", EPMC), FakeRetriever("litsense", LS)
    result, params = _agg(epmc, ls, max_documents=5).search("q")
    assert [d.source for d in result.documents] == [
        "europe_pmc", "litsense", "europe_pmc", "litsense", "europe_pmc",
    ]  # fmt: skip
    assert result.per_source_counts == {"europe_pmc": 3, "litsense": 2}
    assert epmc.queries == ls.queries == ["q"]
    assert params["raw_counts"] == {"europe_pmc": 5, "litsense": 5}
    assert params["per_source"]["litsense"]["fake"] is True
    assert params["failed_sources"] == []


def test_one_source_cannot_monopolize_when_other_is_short() -> None:
    epmc = FakeRetriever("europe_pmc", EPMC)
    ls = FakeRetriever("litsense", LS[:1])
    result, _ = _agg(epmc, ls, max_documents=4).search("q")
    assert [d.doc_id for d in result.documents] == ["PMID:0", "PMID:100#S-0", "PMID:1", "PMID:2"]


def test_dedupe_by_identifier_and_near_identical_text() -> None:
    docs = [
        _doc("europe_pmc", "PMID:1", "Fever is common in adults with colds."),
        _doc("europe_pmc", "pmid:1 ", "Different text but same identifier."),
        _doc("europe_pmc", "PMID:2", "A completely different abstract."),
    ]
    near_copy = _doc("litsense", "PMID:9#S-1", "fever is common in adults with colds")
    result, _ = _agg(
        FakeRetriever("europe_pmc", docs), FakeRetriever("litsense", [near_copy])
    ).search("q")
    assert [d.doc_id for d in result.documents] == ["PMID:1", "PMID:2"]


def test_empty_text_dropped_and_long_text_truncated() -> None:
    docs = [_doc("europe_pmc", "PMID:1", ""), _doc("europe_pmc", "PMID:2", "word " * 400)]
    result, _ = _agg(FakeRetriever("europe_pmc", docs), max_doc_chars=120).search("q")
    assert [d.doc_id for d in result.documents] == ["PMID:2"]
    assert len(result.documents[0].text) == 120
    assert result.documents[0].text.endswith("…")


def test_failing_source_is_non_fatal() -> None:
    bad = FakeRetriever("europe_pmc", RetrieverError("europe_pmc", "HTTP 500: down"))
    result, params = _agg(bad, FakeRetriever("litsense", LS)).search("q")
    assert len(result.documents) == 5
    assert result.errors == ["europe_pmc: HTTP 500: down"]
    assert result.per_source_counts == {"europe_pmc": 0, "litsense": 5}
    assert params["failed_sources"] == ["europe_pmc"]


def test_unexpected_exception_is_also_non_fatal() -> None:
    bad = FakeRetriever("litsense", ValueError("parser exploded"))
    result, params = _agg(FakeRetriever("europe_pmc", EPMC), bad).search("q")
    assert len(result.documents) == 5
    assert "litsense: unexpected ValueError" in result.errors[0]
    assert params["failed_sources"] == ["litsense"]


def test_both_sources_fail() -> None:
    result, params = _agg(
        FakeRetriever("europe_pmc", RetrieverError("europe_pmc", "timeout")),
        FakeRetriever("litsense", RetrieverError("litsense", "HTTP 503")),
    ).search("q")
    assert result.documents == []
    assert len(result.errors) == 2
    assert params["failed_sources"] == ["europe_pmc", "litsense"]


# --- structured queries: relaxation ladder and reranking ----------------------------------------

LQ = LiteratureQuery(
    keywords="serum sodium adrenal insufficiency",
    variable_terms=["serum sodium", "hyponatremia"],
    condition_terms=["primary adrenal insufficiency"],
    related_condition_terms=["adrenal crisis"],
    expected_answer_type="numeric",
)


class ScriptedRetriever:
    """Returns canned documents per exact query string."""

    def __init__(
        self, name: str, responses: dict[str, list[RetrievedDocument] | Exception]
    ) -> None:
        self.name = name
        self.responses = responses
        self.queries: list[str] = []

    def search(self, query: str, **params: Any) -> list[RetrievedDocument]:
        self.queries.append(query)
        response = self.responses.get(query, [])
        if isinstance(response, Exception):
            raise response
        return list(response)

    def parameters(self) -> dict[str, Any]:
        return {"endpoint": f"https://{self.name}.test"}


def _ladder(source: str) -> list[str]:
    return [attempt.query for attempt in query_ladder(source, LQ)]


def test_relaxes_until_enough_documents_mention_the_variable() -> None:
    strict, related, *_ = _ladder("europe_pmc")
    retriever = ScriptedRetriever("europe_pmc", {
        strict: [_doc("europe_pmc", "PMID:1", "Hyponatremia in primary adrenal insufficiency."),
                 _doc("europe_pmc", "PMID:2", "Adrenal insufficiency imaging findings.")],
        related: [_doc("europe_pmc", "PMID:1", "Hyponatremia in primary adrenal insufficiency."),
                  _doc("europe_pmc", "PMID:3", "Serum sodium was 128 mmol/L in adrenal crisis."),
                  _doc("europe_pmc", "PMID:4", "Hyponatremia during adrenal crisis.")],
    })  # fmt: skip
    result, params = _agg(retriever).search(LQ)

    assert retriever.queries == [strict, related]
    attempts = params["per_source"]["europe_pmc"]["query_attempts"]
    assert [(a["level"], a["returned"], a["new"], a["relevant_total"]) for a in attempts] == [
        ("variable_and_condition", 2, 2, 1),
        ("variable_and_related_condition", 3, 2, 3),
    ]
    assert params["raw_counts"] == {"europe_pmc": 4}
    assert result.query == related


def test_no_relaxation_when_strict_query_is_enough() -> None:
    strict = _ladder("europe_pmc")[0]
    docs = [_doc("europe_pmc", f"PMID:{i}", f"Serum sodium level {i} in adrenal insufficiency.")
            for i in range(3)]  # fmt: skip
    retriever = ScriptedRetriever("europe_pmc", {strict: docs})
    _agg(retriever).search(LQ)
    assert retriever.queries == [strict]


def test_rerank_puts_relevant_documents_first() -> None:
    strict = _ladder("litsense")[0]
    docs = [
        _doc("litsense", "PMID:1#A-1", "Adrenal gland anatomy overview."),
        _doc("litsense", "PMID:2#A-2", "Hyponatremia is frequent in adrenal insufficiency."),
        _doc(
            "litsense",
            "PMID:3#A-3",
            "Serum sodium was 126 mmol/L in primary adrenal insufficiency.",
        ),
    ]
    reranked, _ = _agg(ScriptedRetriever("litsense", {strict: docs})).search(LQ)
    assert [d.doc_id for d in reranked.documents] == ["PMID:3#A-3", "PMID:2#A-2", "PMID:1#A-1"]

    plain = RetrievalAggregator(
        [ScriptedRetriever("litsense", {strict: docs})],
        max_documents=10, max_doc_chars=1000, rerank=False,
    ).search(LQ)[0]  # fmt: skip
    assert [d.doc_id for d in plain.documents] == ["PMID:1#A-1", "PMID:2#A-2", "PMID:3#A-3"]


def test_error_after_partial_results_keeps_documents() -> None:
    strict, related, *_ = _ladder("europe_pmc")
    retriever = ScriptedRetriever("europe_pmc", {
        strict: [_doc("europe_pmc", "PMID:1", "Hyponatremia in adrenal insufficiency.")],
        related: RetrieverError("europe_pmc", "HTTP 503: busy"),
    })  # fmt: skip
    result, params = _agg(retriever).search(LQ)
    assert [d.doc_id for d in result.documents] == ["PMID:1"]
    assert result.errors == ["europe_pmc: HTTP 503: busy"]
    assert params["failed_sources"] == []
    assert params["per_source"]["europe_pmc"]["query_attempts"][-1]["error"] == (
        "europe_pmc: HTTP 503: busy"
    )


def test_query_label_names_each_source_when_queries_differ() -> None:
    result, _ = _agg(ScriptedRetriever("europe_pmc", {}), ScriptedRetriever("litsense", {})).search(
        LQ
    )
    europe_pmc_last, litsense_last = _ladder("europe_pmc")[-1], _ladder("litsense")[-1]
    assert result.query == f"europe_pmc: {europe_pmc_last} | litsense: {litsense_last}"
