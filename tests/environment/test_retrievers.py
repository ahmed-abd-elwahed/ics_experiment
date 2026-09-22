from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest
import respx

from medsim.config import EuropePMCSettings, LitSenseSettings
from medsim.errors import RetrieverError
from medsim.http_utils import RateLimiter
from medsim.retrieval.base import strip_html
from medsim.retrieval.cache import ResponseCache
from medsim.retrieval.europe_pmc import EuropePMCRetriever
from medsim.retrieval.litsense import LitSenseRetriever
from tests.conftest import load_fixture

EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
LS_BASE = "https://www.ncbi.nlm.nih.gov/research/litsense2-api/api"
UA = "medsim-test/0.1 (mailto:test@example.org)"


def _epmc(cache: ResponseCache | None = None, **overrides: object) -> EuropePMCRetriever:
    cfg = EuropePMCSettings.model_validate({"backoff_base_s": 0.0, "max_retries": 1, **overrides})
    return EuropePMCRetriever(cfg, user_agent=UA, cache=cache, sleep=lambda _: None)


def _litsense(**overrides: object) -> LitSenseRetriever:
    cfg = LitSenseSettings.model_validate(
        {"backoff_base_s": 0.0, "max_retries": 1, "min_interval_s": 0.0, **overrides}
    )
    return LitSenseRetriever(cfg, user_agent=UA, sleep=lambda _: None)


# --- Europe PMC ---------------------------------------------------------------------------------


def test_europe_pmc_parses_recorded_response() -> None:
    docs = EuropePMCRetriever.parse(load_fixture("europe_pmc_search_core.json"))
    assert len(docs) == 5
    first = docs[0]
    assert first.source == "europe_pmc"
    assert first.doc_id == "PMID:42016338"
    assert first.url == "https://pubmed.ncbi.nlm.nih.gov/42016338/"
    assert first.text.startswith("While normal human body temperature")
    assert re.search(r"</?[A-Za-z][^<>]*>", first.text) is None
    assert "(< 35 °C)" in first.text
    assert first.raw["pmcid"] == "PMC13094164"


def test_strip_html_keeps_comparison_signs() -> None:
    raw = "<h4>Background</h4>hypothermia (< 35 °C) in adults &gt; 65 <i>years</i>"
    assert strip_html(raw) == "Background hypothermia (< 35 °C) in adults > 65 years"


def test_europe_pmc_sends_documented_params_and_records_them(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(url__startswith=EPMC_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("europe_pmc_search_core.json"))
    )
    retriever = _epmc(open_access_only=True, full_text_only=True, sort="CITED desc")
    docs = retriever.search("fever common cold", page_size=3)

    request = route.calls.last.request
    params = dict(request.url.params)
    assert params == {
        "query": "(fever common cold) AND OPEN_ACCESS:y AND HAS_FT:y",
        "resultType": "core",
        "pageSize": "3",
        "format": "json",
        "synonym": "false",
        "cursorMark": "*",
        "sort": "CITED desc",
    }
    assert request.headers["User-Agent"] == UA
    recorded = retriever.parameters()
    assert recorded["request_params"] == params
    assert recorded["page_size"] == 3
    assert recorded["endpoint"] == EPMC_URL
    assert len(docs) == 5


def test_europe_pmc_zero_hits(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(url__startswith=EPMC_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("europe_pmc_search_empty.json"))
    )
    assert _epmc().search("qzxvkjw") == []


def test_europe_pmc_retries_5xx(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(url__startswith=EPMC_URL).mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=load_fixture("europe_pmc_search_empty.json")),
        ]
    )
    assert _epmc().search("x") == []
    assert route.call_count == 2


def test_europe_pmc_persistent_failure_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(url__startswith=EPMC_URL).mock(return_value=httpx.Response(500, text="down"))
    with pytest.raises(RetrieverError, match="europe_pmc: HTTP 500"):
        _epmc().search("x")


def test_europe_pmc_cache_replays_without_http(
    respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    route = respx_mock.get(url__startswith=EPMC_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("europe_pmc_search_core.json"))
    )
    retriever = _epmc(cache=ResponseCache(tmp_path))
    first = retriever.search("fever")
    assert retriever.parameters()["cache_hit"] is False
    second = retriever.search("fever")
    assert retriever.parameters()["cache_hit"] is True
    assert route.call_count == 1
    assert first == second
    retriever.search("fever", page_size=2)  # different params -> different cache key
    assert route.call_count == 2


# --- LitSense -----------------------------------------------------------------------------------


def test_litsense_parses_recorded_passages() -> None:
    docs = LitSenseRetriever.parse(load_fixture("litsense_passages.json"))
    assert len(docs) == 100
    assert all(d.source == "litsense" and d.title is None for d in docs)
    assert all(d.doc_id.startswith(("PMID:", "PMCID:")) and "#" in d.doc_id for d in docs)
    assert all(isinstance(d.score, float) for d in docs)
    assert len({d.doc_id for d in docs}) == len(docs)


def test_litsense_request_and_truncation(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(url__startswith=f"{LS_BASE}/sentences/").mock(
        return_value=httpx.Response(200, json=load_fixture("litsense_sentences.json"))
    )
    retriever = _litsense(mode="sentences", max_results=5)
    docs = retriever.search("body temperature common cold")
    request = route.calls.last.request
    assert request.url.path == "/research/litsense2-api/api/sentences/"
    assert dict(request.url.params) == {"query": "body temperature common cold", "rerank": "true"}
    assert len(docs) == 5
    assert retriever.parameters()["result_type"] == "sentences"


def test_litsense_404_no_match_is_zero_results(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(url__startswith=f"{LS_BASE}/passages/").mock(
        return_value=httpx.Response(404, json=load_fixture("litsense_passages_no_match_404.json"))
    )
    retriever = _litsense()
    assert retriever.search("qzxvkjw") == []
    assert retriever.parameters()["no_match"] is True


def test_litsense_other_404_is_an_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(url__startswith=f"{LS_BASE}/passages/").mock(
        return_value=httpx.Response(404, text="<html>Not Found</html>")
    )
    with pytest.raises(RetrieverError, match="litsense: HTTP 404"):
        _litsense().search("x")


def test_rate_limiter_enforces_min_interval() -> None:
    now = [100.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    limiter = RateLimiter(1.0, clock=lambda: now[0], sleep=sleep)
    limiter.wait()
    now[0] += 0.25
    limiter.wait()
    now[0] += 2.0
    limiter.wait()
    assert slept == [pytest.approx(0.75)]


@respx.mock
def test_europe_pmc_retries_replies_without_results_and_never_caches_them(tmp_path: Path) -> None:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    good = load_fixture("europe_pmc_search_core.json")
    route = respx.get(url).mock(
        side_effect=[httpx.Response(200, json={"version": "6.9"}), httpx.Response(200, json=good)]
    )
    cache = ResponseCache(tmp_path)
    settings = EuropePMCSettings(backoff_base_s=0.0, max_retries=1)
    retriever = EuropePMCRetriever(settings, user_agent="t", cache=cache, sleep=lambda _s: None)
    assert retriever.search("q")
    assert route.call_count == 2

    respx.get(url).mock(return_value=httpx.Response(200, json={"version": "6.9"}))
    fresh = EuropePMCRetriever(settings, user_agent="t", sleep=lambda _s: None)
    with pytest.raises(RetrieverError, match="after 2 attempts"):
        fresh.search("other query")

    params = retriever.build_request("stale", settings)[1]
    cache.set("europe_pmc", "stale", params, {"version": "6.9"})  # written by an older version
    respx.get(url).mock(return_value=httpx.Response(200, json=good))
    assert retriever.search("stale")
    assert retriever.parameters()["cache_hit"] is False
