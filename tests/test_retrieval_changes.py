"""Retrieval changes 1-6 (results/README.md): each is off by default and tested on its own."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from bench.run import CONFIGS, RETRIEVAL_STAGES
from medsim import rules
from medsim.environment import MedicalEnvironment, build_aggregator
from medsim.models import CaseStudy, LiteratureQuery, RetrievedDocument, SourceName
from medsim.retrieval.aggregator import RetrievalAggregator
from medsim.retrieval.cache import ResponseCache
from medsim.retrieval.fulltext import FullTextFetcher, parse_blocks
from medsim.retrieval.population import non_human
from medsim.retrieval.query_formulation import (
    LadderOptions,
    RelevanceScorer,
    age_mismatch,
    excerpt,
    query_ladder,
)
from medsim.retrieval.rerank import LLMReranker
from tests.conftest import ScriptedLLM, make_settings
from tests.test_aggregator import FakeRetriever
from tests.test_environment import builder, resolver, synth

LQ = LiteratureQuery(
    keywords="albumin biloma",
    variable_terms=["serum albumin", "hypoalbuminemia"],
    condition_terms=["biloma", "bile leak"],
    related_condition_terms=["biliary injury"],
    context_terms=["elderly"],
    expected_answer_type="numeric",
    patient_age_group="adult",
)


def _doc(
    doc_id: str,
    text: str,
    *,
    source: SourceName = "europe_pmc",
    title: str | None = None,
    **raw: Any,
) -> RetrievedDocument:
    return RetrievedDocument(
        source=source, doc_id=doc_id, title=title, text=text, url=None, score=None, raw=raw
    )


# --- patient age and population -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "group"),
    [
        ("A 75-year-old female presented", "adult"),
        ("A 2270 g male newborn born to a 25-year-old mother", "neonate"),
        ("A 6-month-old boy", "child"),
        ("A 12-year-old girl", "child"),
        ("patient aged 45 years", "adult"),
        ("A 3-day-old infant", "neonate"),
        ("no age given", None),
    ],
)
def test_age_group(text: str, group: str | None) -> None:
    assert rules.age_group(text) == group


def test_non_human_uses_each_sources_metadata() -> None:
    mesh = {"meshHeading": [{"descriptorName": "Animals"}, {"descriptorName": "Dogs"}]}
    assert non_human(_doc("PMID:1", "t", meshHeadingList=mesh))
    both = {"meshHeading": [{"descriptorName": "Animals"}, {"descriptorName": "Humans"}]}
    assert not non_human(_doc("PMID:2", "t", meshHeadingList=both))
    mouse = ["1|5|species|10090"]
    assert non_human(_doc("PMID:3#R", "t", source="litsense", annotations=mouse))
    mixed = ["1|5|species|10090", "9|8|species|9606"]
    assert not non_human(_doc("PMID:4#R", "t", source="litsense", annotations=mixed))
    bacteria = ["1|5|species|1280"]  # Staphylococcus aureus: not an animal study
    assert not non_human(_doc("PMID:5#R", "t", source="litsense", annotations=bacteria))
    assert non_human(_doc("PMID:6", "t", title="Biloma in a cat with cholelithiasis"))


def test_age_mismatch() -> None:
    assert age_mismatch("Serum albumin in 40 children with bile leak", "adult")
    assert not age_mismatch("Albumin in adults and children with bile leak", "adult")
    assert age_mismatch("Albumin in elderly patients", "child")
    assert not age_mismatch("Albumin in patients", None)


# --- ladders ------------------------------------------------------------------------------------


def test_v1_ladders_are_unchanged() -> None:
    levels = [a.level for a in query_ladder("litsense", LQ)]
    assert levels == [
        "variable_and_condition", "variable_synonym_and_condition",
        "variable_and_related_condition", "variable_reference_values",
    ]  # fmt: skip
    assert query_ladder("litsense", LQ)[0].query == "serum albumin biloma"
    assert query_ladder("europe_pmc", LQ)[-1].level == "variable_reference_values"


def test_v2_ladders_search_bodies_and_drop_unhelpful_rungs() -> None:
    v2 = LadderOptions("v2")
    epmc = query_ladder("europe_pmc", LQ, v2)
    assert [a.level for a in epmc] == [
        "variable_and_condition", "body_variable_and_condition", "variable_and_related_condition",
    ]  # fmt: skip
    assert 'CASE:("serum albumin" OR hypoalbuminemia)' in epmc[1].query
    assert "TABLE:" in epmc[1].query and "RESULTS:" in epmc[1].query
    assert 'TITLE_ABS:(biloma OR "bile leak")' in epmc[1].query
    litsense = query_ladder("litsense", LQ, v2)
    assert [a.level for a in litsense] == [
        "variable_and_condition",
        "variable_and_related_condition",
    ]


def test_natural_litsense_query() -> None:
    ladder = query_ladder("litsense", LQ, LadderOptions("v2", "natural"))
    assert ladder[0].query == "serum albumin in elderly patients with biloma"
    assert ladder[1].query == "serum albumin in elderly patients with biliary injury"


# --- scoring and excerpts -----------------------------------------------------------------------


def test_value_first_scoring_and_penalties() -> None:
    value_only = _doc("A", "Serum albumin was 2.9 g/dL in patients after hepatectomy.")
    condition_only = _doc("B", "Serum albumin is discussed in biloma management.")
    child = _doc("C", "In children with biloma, serum albumin was 3.1 g/dL.")
    original = RelevanceScorer(LQ)
    assert original.score(value_only) == original.score(condition_only)  # 3+2 each
    first = RelevanceScorer(LQ, value_first=True, age_penalty=True, related_penalty=True)
    assert first.score(value_only) > first.score(condition_only)
    assert (
        first.score(child) == first.score(_doc("D", child.text.replace("children", "people"))) - 4
    )
    assert first.score(value_only, "variable_and_related_condition") == first.score(value_only) - 2
    assert first.has_value(value_only) and not first.has_value(condition_only)


def test_excerpt_keeps_value_sentences_in_order() -> None:
    scorer = RelevanceScorer(LQ)
    blocks = [
        "Biloma is a collection of bile. It follows surgery.",
        "On admission the patient was febrile. Serum albumin was 2.3 g/dL. Imaging showed fluid.",
        "Table 1 [Variable | Value]: Serum albumin | 2.3 g/dL.",
    ]
    text = excerpt(blocks, scorer, max_chars=120)
    assert text is not None and len(text) <= 120
    assert "Serum albumin was 2.3 g/dL." in text
    assert excerpt(["Nothing relevant here."], scorer, 200) is None


def test_parse_blocks_reads_paragraphs_and_table_rows() -> None:
    xml = """<article><front><title>x</title></front><body><sec><title>Case</title>
    <p>A 64-year-old man. Serum albumin was <bold>2.3</bold> g/dL.</p>
    <table-wrap><label>Table 1</label><caption><p>Labs</p></caption><table>
    <tr><th>Test</th><th>Value</th></tr><tr><td>Albumin</td><td>2.3 g/dL</td></tr></table>
    </table-wrap><fig><caption><p>ignored</p></caption></fig></sec></body>
    <back><ref-list><p>ref</p></ref-list></back></article>"""
    blocks = parse_blocks(xml)
    assert blocks[0] == "Case."
    assert "Serum albumin was 2.3 g/dL." in blocks[1]
    assert blocks[2] == "Table 1 Labs [Test | Value]: Albumin | 2.3 g/dL."
    assert not any("ignored" in b or b == "ref" for b in blocks)
    assert parse_blocks("not xml") == []


@respx.mock
def test_fulltext_fetcher_caches_hits_and_misses(tmp_path: Path) -> None:
    base = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    ok = respx.get(f"{base}/PMC1/fullTextXML").mock(
        return_value=httpx.Response(
            200, text="<article><body><p>Albumin 2.3 g/dL.</p></body></article>"
        )
    )
    missing = respx.get(f"{base}/PMC2/fullTextXML").mock(return_value=httpx.Response(404))
    fetcher = FullTextFetcher(base_url=base, user_agent="t", cache=ResponseCache(tmp_path))
    assert fetcher.blocks("PMC1") == ["Albumin 2.3 g/dL."]
    assert fetcher.blocks("PMC1") == ["Albumin 2.3 g/dL."]
    assert fetcher.blocks("PMC2") is None
    assert fetcher.blocks("PMC2") is None
    assert ok.call_count == 1 and missing.call_count == 1


# --- the aggregator -----------------------------------------------------------------------------


class FakeFullText:
    def __init__(self, blocks: dict[str, list[str]]) -> None:
        self._blocks = blocks

    def blocks(self, pmcid: str) -> list[str] | None:
        return self._blocks.get(pmcid)


def test_improved_aggregator_end_to_end() -> None:
    long_abstract = "Background sentence. " * 100 + "Serum albumin was 2.8 g/dL in biloma."
    epmc = FakeRetriever("europe_pmc", [
        _doc("PMID:1", "Biloma after surgery; albumin not reported."),
        _doc("PMID:2", "Dogs with biloma.", meshHeadingList={
            "meshHeading": [{"descriptorName": "Animals"}]}),
        _doc("PMID:3", long_abstract),
        _doc("PMID:4", "Case of biloma.", pmcid="PMC4", isOpenAccess="Y"),
    ])  # fmt: skip
    litsense = FakeRetriever("litsense", [
        _doc("PMID:9#R", "Serum albumin 3.0 g/dL in bile leak.", source="litsense"),
    ])  # fmt: skip
    body = ["The case report.", "Laboratory: serum albumin 2.1 g/dL, bilirubin 3 mg/dL."]
    agg = RetrievalAggregator(
        [epmc, litsense], max_documents=3, max_doc_chars=200, value_first=True, merge="global",
        population_filter=True, ladder=LadderOptions("v2"), excerpts=True,
        fulltext=FakeFullText({"PMC4": body}),  # type: ignore[arg-type]
    )  # fmt: skip
    result, params = agg.search(LQ)
    ids = [d.doc_id for d in result.documents]
    assert "PMID:2" not in ids  # animal study dropped
    assert params["population_filtered"] == {"europe_pmc": 1, "litsense": 0}
    assert set(ids) == {"PMID:3", "PMID:4", "PMID:9#R"}  # the three that state a value
    by_id = {d.doc_id: d for d in result.documents}
    assert "serum albumin 2.1 g/dL" in by_id["PMID:4"].text  # from the full text
    assert by_id["PMID:3"].text.startswith("Background sentence.")  # window, not head
    assert "2.8 g/dL" in by_id["PMID:3"].text and len(by_id["PMID:3"].text) <= 200
    assert params["excerpts"] == {"full_text_fetched": 1, "full_text_used": 1, "windows": 1}
    # v2 broadens on documents stating a value: 2 < 3, so every Europe PMC rung ran
    assert len(epmc.queries) == 3


def test_llm_rerank_orders_picks_first_and_records_the_call() -> None:
    llm = ScriptedLLM([{"reasoning": "C2 states a value", "selected_ids": ["C2", "C9", "c2"]}])
    docs = [_doc(f"PMID:{i}", f"serum albumin in biloma, study {i}") for i in range(3)]
    agg = RetrievalAggregator(
        [FakeRetriever("europe_pmc", docs)], max_documents=2, max_doc_chars=500,
        reranker=LLMReranker(llm), rerank_candidates=3,
    )  # fmt: skip
    records: list[Any] = []
    result, params = agg.search(LQ, records=records)
    assert [d.doc_id for d in result.documents] == ["PMID:1", "PMID:0"]
    assert params["llm_rerank"] == {"candidates": 3, "selected": 1}
    assert [r.stage for r in records] == ["reranker"]


def test_llm_rerank_failure_keeps_lexical_order() -> None:
    from medsim.errors import LLMError

    llm = ScriptedLLM([LLMError("down")])
    docs = [_doc(f"PMID:{i}", f"serum albumin in biloma {i}") for i in range(3)]
    agg = RetrievalAggregator(
        [FakeRetriever("europe_pmc", docs)], max_documents=2, max_doc_chars=500,
        reranker=LLMReranker(llm),
    )  # fmt: skip
    result, params = agg.search(LQ, records=[])
    assert len(result.documents) == 2
    assert "error" in params["llm_rerank"]


def test_defaults_build_the_original_aggregator() -> None:
    agg = build_aggregator(make_settings(), [FakeRetriever("europe_pmc", [])], ScriptedLLM())
    assert (agg.merge, agg.value_first, agg.population_filter) == ("round_robin", False, False)
    assert (agg.ladder, agg.excerpts, agg.reranker) == (LadderOptions(), False, None)


def test_environment_passes_age_group_and_records_rerank_calls(case: CaseStudy) -> None:
    terms = {"variable_terms": ["body temperature"], "condition_terms": ["common cold"],
             "related_condition_terms": [], "context_terms": []}  # fmt: skip
    llm = ScriptedLLM([
        resolver(), {**builder(), **terms}, {"reasoning": "r", "selected_ids": ["C1"]},
        synth(ids=["PMID:1"]),
    ])  # fmt: skip
    docs = [_doc("PMID:1", "Body temperature 37.5-39.0 °C in adults with colds.")]
    settings = make_settings(llm_rerank=True)
    retriever = FakeRetriever("europe_pmc", docs)
    env = MedicalEnvironment(case_study=case, llm=llm, retrievers=[retriever], settings=settings)
    response = env.query("What is the patient's temperature on day 4?")
    assert [c.stage for c in response.llm_calls] == [
        "resolver", "query_builder", "reranker", "synthesizer",
    ]  # fmt: skip
    assert env._age_group == "adult"


def test_bench_configs_for_the_changes() -> None:
    settings = make_settings()
    four = CONFIGS["improved_1to4"].settings(settings)
    assert (four.rank_for_values, four.merge_strategy, four.population_filter) == (
        True, "global", True,
    )  # fmt: skip
    assert (four.ladder_version, four.fulltext_excerpts, four.europe_pmc.page_size) == (
        "v2", True, 50,
    )  # fmt: skip
    assert four.litsense.query_style == "keywords" and not four.llm_rerank
    five = CONFIGS["improved_1to5"].settings(settings)
    assert five.litsense.query_style == "natural" and not five.llm_rerank
    six = CONFIGS["improved_1to6"].settings(settings)
    assert six.litsense.query_style == "natural" and six.llm_rerank
    assert "reranker" in RETRIEVAL_STAGES


# --- concurrency and transient faults ------------------------------------------------------------


def test_cache_survives_concurrent_writers_of_one_key(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    cache = ResponseCache(tmp_path)
    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(lambda i: cache.set("s", "q", {}, {"n": i}), range(200)))
    assert cache.get("s", "q", {}) is not None
    assert not list(tmp_path.rglob("*.tmp"))


@respx.mock
def test_openrouter_retries_empty_replies() -> None:
    from medsim.llm.openrouter import OpenRouterClient
    from medsim.models import ChatMessage
    from tests.conftest import completion_body

    empty = completion_body("")
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(200, json=empty),
            httpx.Response(200, json=completion_body("ok")),
        ]
    )
    with OpenRouterClient(make_settings()) as client:
        client._sleep = lambda _s: None
        reply = client.complete(
            [ChatMessage(role="user", content="q")], response_format=None, temperature=0,
            max_tokens=10,
        )  # fmt: skip
    assert reply.content == "ok" and route.call_count == 2


def test_run_configs_share_one_pool_and_write_each_configuration(tmp_path: Path) -> None:
    from bench.run import run_configs
    from bench.schemas import Item, RunRecord
    from bench.workspace import Workspace, read_models

    item = Item(
        item_id="B:x:hr", question_set="B", case_id="x", diagnosis="d", question="q?",
        variable="heart rate", category="vital_sign",
        case=CaseStudy(case_id="x", diagnosis="d", narrative="n"), patient="p",
    )  # fmt: skip
    llm = ScriptedLLM([resolver(answerable=True, answer="HR 80", spans=["n"])] * 2)
    ws = Workspace(tmp_path)
    summary = run_configs(
        ws, [item], [CONFIGS["current"], CONFIGS["improved_1to4"]], llm=llm,
        base_settings=make_settings(), retrievers=lambda s: [FakeRetriever("europe_pmc", [])],
        workers=2,
    )  # fmt: skip
    assert set(summary) == {"current", "improved_1to4"}
    for name in summary:
        [record] = read_models(ws.run_file(name), RunRecord)
        assert record.path == "case_study"


def test_web_search_pmc_hits_get_full_text_excerpts() -> None:
    web = FakeRetriever("openrouter_search", [
        _doc("PMCID:PMC7", "A case of biloma after cholecystectomy.", source="openrouter_search",
             pmcid="PMC7"),
        _doc("URL:site/x", "Biloma overview.", source="openrouter_search"),
    ])  # fmt: skip
    agg = RetrievalAggregator(
        [web], max_documents=2, max_doc_chars=300, value_first=True, merge="global",
        excerpts=True, fulltext=FakeFullText({"PMC7": ["Serum albumin was 2.2 g/dL on day 2."]}),  # type: ignore[arg-type]
    )  # fmt: skip
    result, params = agg.search(LQ)
    assert result.documents[0].doc_id == "PMCID:PMC7"
    assert "2.2 g/dL" in result.documents[0].text
    assert params["excerpts"]["full_text_used"] == 1


def test_improved_openrouter_config() -> None:
    s = CONFIGS["openrouter_search_improved"].settings(make_settings())
    assert s.enabled_sources == ["openrouter_search"]
    assert (s.openrouter_search.max_results, s.openrouter_search.max_characters) == (10, 3000)
    assert s.rank_for_values and s.fulltext_excerpts and s.population_filter
    assert not s.llm_rerank
