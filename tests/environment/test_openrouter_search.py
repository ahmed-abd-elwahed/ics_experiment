from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from medsim.environment import build_retrievers
from medsim.errors import RetrieverError
from medsim.llm.openrouter import OpenRouterClient
from medsim.llm.structured import call_structured
from medsim.models import ChatMessage, LiteratureQuery, LLMCallRecord, ResolverOutput
from medsim.retrieval.aggregator import RetrievalAggregator
from medsim.retrieval.cache import ResponseCache
from medsim.retrieval.openrouter_search import (
    OpenRouterSearchRetriever,
    doc_id_for,
    identifiers_from_url,
)
from medsim.retrieval.query_formulation import query_ladder
from tests.conftest import TEST_KEY, completion_body, load_fixture, make_settings

URL = "https://openrouter.ai/api/v1/chat/completions"


def _retriever(**overrides: object) -> OpenRouterSearchRetriever:
    settings = make_settings(**overrides)
    retriever = OpenRouterSearchRetriever.from_settings(settings)
    retriever._sleep = lambda _s: None
    return retriever


def test_identifiers_and_doc_ids_from_urls() -> None:
    assert identifiers_from_url("https://pmc.ncbi.nlm.nih.gov/articles/PMC8576027/") == (
        None,
        "PMC8576027",
    )
    assert identifiers_from_url("https://pubmed.ncbi.nlm.nih.gov/6533196/") == ("6533196", None)
    assert doc_id_for("https://europepmc.org/article/MED/40546790") == "PMID:40546790"
    assert doc_id_for("https://www.ncbi.nlm.nih.gov/books/NBK526121/") == (
        "URL:ncbi.nlm.nih.gov/books/NBK526121"
    )


def test_parse_recorded_response_returns_every_citation() -> None:
    docs = OpenRouterSearchRetriever.parse(load_fixture("openrouter_web_search.json"))
    assert len(docs) == 8
    assert docs[0].doc_id == "PMCID:PMC12714918"
    assert docs[0].source == "openrouter_search"
    assert docs[0].raw["pmcid"] == "PMC12714918"
    assert docs[2].doc_id == "PMID:6533196"
    assert all(d.text for d in docs)


def test_build_request_bounds_the_search() -> None:
    retriever = _retriever()
    body = retriever.build_request("q", retriever.settings)
    tool = body["tools"][0]
    assert tool["type"] == "openrouter:web_search"
    assert tool["parameters"]["max_uses"] == 1
    assert tool["parameters"]["engine"] == "exa"
    assert tool["parameters"]["max_results"] == 8
    assert "ncbi.nlm.nih.gov" in tool["parameters"]["allowed_domains"]
    assert body["messages"][-1] == {"role": "user", "content": "q"}


@respx.mock
def test_search_reports_cost_and_replays_cost_from_cache(tmp_path: Path) -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json=load_fixture("openrouter_web_search.json"))
    )
    retriever = _retriever()
    retriever._cache = ResponseCache(tmp_path)
    docs = retriever.search("serum bilirubin in patients with tricuspid regurgitation")
    assert len(docs) == 8
    params = retriever.parameters()
    assert params["cost_usd"] == pytest.approx(0.00713932)
    assert params["web_search_requests"] == 1
    assert params["cache_hit"] is False
    sent = json.loads(route.calls[0].request.content)
    assert route.calls[0].request.headers["Authorization"] == f"Bearer {TEST_KEY}"
    assert sent["tools"][0]["parameters"]["max_uses"] == 1

    again = retriever.search("serum bilirubin in patients with tricuspid regurgitation")
    assert [d.doc_id for d in again] == [d.doc_id for d in docs]
    assert route.call_count == 1
    assert retriever.parameters()["cache_hit"] is True
    assert retriever.parameters()["cost_usd"] == pytest.approx(0.00713932)


@respx.mock
def test_http_error_is_a_retriever_error_without_the_key() -> None:
    respx.post(URL).mock(return_value=httpx.Response(402, text=f"no credits for {TEST_KEY}"))
    with pytest.raises(RetrieverError) as info:
        _retriever().search("q")
    assert "402" in str(info.value)
    assert TEST_KEY not in str(info.value)


def test_web_search_ladder_is_one_natural_language_query() -> None:
    lq = LiteratureQuery(
        keywords="k",
        variable_terms=["total bilirubin", "hyperbilirubinemia"],
        condition_terms=["tricuspid regurgitation"],
        related_condition_terms=["right heart failure"],
        context_terms=["elderly"],
    )
    ladder = query_ladder("openrouter_search", lq)
    assert [a.query for a in ladder] == [
        "total bilirubin in elderly patients with tricuspid regurgitation"
    ]


@respx.mock
def test_aggregator_records_search_cost_per_attempt() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(200, json=load_fixture("openrouter_web_search.json"))
    )
    agg = RetrievalAggregator([_retriever()], max_documents=5, max_doc_chars=500)
    lq = LiteratureQuery(
        keywords="k", variable_terms=["bilirubin"], condition_terms=["tricuspid regurgitation"]
    )
    result, params = agg.search(lq)
    assert len(result.documents) == 5
    attempts = params["per_source"]["openrouter_search"]["query_attempts"]
    assert attempts[0]["cost_usd"] == pytest.approx(0.00713932)


def test_build_retrievers_knows_openrouter_search() -> None:
    settings = make_settings(enabled_sources=["openrouter_search"])
    [retriever] = build_retrievers(settings)
    assert retriever.name == "openrouter_search"


@respx.mock
def test_llm_call_records_carry_openrouter_cost() -> None:
    body = completion_body(
        json.dumps(
            {"answerable_from_case": False, "answer": None, "evidence_spans": [],
             "reasoning": "r", "query_scope": "patient", "partial_facts": []}
        )
    )  # fmt: skip
    body["usage"]["cost"] = 0.00012
    respx.post(URL).mock(return_value=httpx.Response(200, json=body))
    records: list[LLMCallRecord] = []
    with OpenRouterClient(make_settings()) as client:
        call_structured(
            client, stage="resolver", messages=[ChatMessage(role="user", content="q")],
            output_model=ResolverOutput, temperature=0.0, max_tokens=100, model=None,
            records=records,
        )  # fmt: skip
    assert records[0].cost_usd == pytest.approx(0.00012)


def _native_reply(content: str, citations: list[dict[str, object]]) -> dict[str, object]:
    annotations = [{"type": "url_citation", "url_citation": c} for c in citations]
    return {
        "choices": [{"message": {"content": content, "annotations": annotations}}],
        "usage": {"cost": 0.01, "server_tool_use_details": {"web_search_requests": 1}},
    }


def test_native_search_asks_for_cited_sources_and_uses_the_cited_text(
    respx_mock: respx.MockRouter,
) -> None:
    line1 = "- **Renal function in TR** — “Creatinine was 1.4 mg/dL.” ([pubmed](https://pubmed.ncbi.nlm.nih.gov/111/))"
    line2 = "- **Another study** — “eGFR was 51.” ([pmc](https://pmc.ncbi.nlm.nih.gov/articles/PMC222/))"
    content = f"{line1}\n{line2}"
    reply = _native_reply(content, [
        {"url": "https://pubmed.ncbi.nlm.nih.gov/111/", "title": "Renal function in TR",
         "start_index": content.index("([pubmed"), "end_index": len(line1)},
        {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC222/", "title": "Another study",
         "start_index": content.index("([pmc"), "end_index": len(content)},
    ])  # fmt: skip
    route = respx_mock.post(URL).mock(return_value=httpx.Response(200, json=reply))
    retriever = _retriever(
        openrouter_search={"engine": "native", "model": "openai/gpt-6-luna", "max_results": 8}
    )
    docs = retriever.search("creatinine tricuspid regurgitation")
    body = json.loads(route.calls.last.request.content)
    assert "list up to 8 relevant sources" in body["messages"][0]["content"]
    assert [d.doc_id for d in docs] == ["PMID:111", "PMCID:PMC222"]
    assert docs[0].text == "Renal function in TR — “Creatinine was 1.4 mg/dL.”"
    assert docs[1].text == "Another study — “eGFR was 51.”"


def test_native_google_search_merges_passages_and_resolves_redirects(
    respx_mock: respx.MockRouter,
) -> None:
    redirect = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AbC="
    content = "TR is linked to renal dysfunction.\nSevere TR had eGFR 51 mL/min."
    reply = _native_reply(content, [
        {"url": redirect, "title": "nih.gov", "start_index": 0, "end_index": 34},
        {"url": redirect, "title": "nih.gov", "start_index": 35, "end_index": len(content)},
    ])  # fmt: skip
    respx_mock.post(URL).mock(return_value=httpx.Response(200, json=reply))
    respx_mock.head(redirect).mock(
        return_value=httpx.Response(
            302, headers={"location": "https://pubmed.ncbi.nlm.nih.gov/19041045/"}
        )
    )
    retriever = _retriever(
        openrouter_search={"engine": "native", "model": "google/gemini-3.1-flash-lite"}
    )
    [doc] = retriever.search("creatinine tricuspid regurgitation")
    assert (doc.doc_id, doc.url, doc.title) == (
        "PMID:19041045", "https://pubmed.ncbi.nlm.nih.gov/19041045/", None
    )  # fmt: skip
    assert doc.raw["pmid"] == "19041045" and doc.raw["redirect_url"] == redirect
    assert doc.text == "TR is linked to renal dysfunction. […] Severe TR had eGFR 51 mL/min."


def test_other_engines_keep_the_single_search_prompt(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(URL).mock(
        return_value=httpx.Response(200, json=load_fixture("openrouter_web_search.json"))
    )
    _retriever().search("creatinine tricuspid regurgitation")
    assert (
        "reply with the single word DONE"
        in json.loads(route.calls.last.request.content)["messages"][0]["content"]
    )
