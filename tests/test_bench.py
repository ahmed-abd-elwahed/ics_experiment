from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bench.extract import check_facts, run_extract
from bench.items import ItemBuilder, question_for, run_redact
from bench.judge import Judge, relevance_grade, run_judge, usefulness_grade
from bench.report import build_report
from bench.run import CONFIGS, SourceArticleFilter, condition_blind, run_configs
from bench.schemas import ExtractedFact, Item, Pass1Output, RunRecord
from bench.stats import cluster_bootstrap, cohen_kappa
from bench.text import (
    case_from_record,
    check_redaction,
    count_value,
    quote_found,
    source_pmcid,
)
from bench.workspace import Workspace, read_models
from medsim.models import LiteratureQuery, RetrievedDocument
from tests.conftest import ScriptedLLM, make_settings
from tests.test_aggregator import FakeRetriever

RECORD = {
    "case_id": "PMC123456_01",
    "diagnosis": "Tricuspid valve regurgitation",
    "chunked_case_info": [
        "A 75-year-old woman had dyspnea. Exam: pulse 80/min, BP 100/60 mmHg, bibasal crackles. "
        "Serum creatinine was 2.4 mg/dL on admission."
    ],
    "background_and_presentation": "A 75-year-old woman presented with dyspnea.",
}


def _fact(**overrides: Any) -> dict[str, Any]:
    fact = {
        "variable": "serum creatinine", "value": "2.4", "unit": "mg/dL",
        "timepoint": "on admission", "span": "Serum creatinine was 2.4 mg/dL on admission",
        "category": "laboratory", "askable_without_diagnosis": True,
        "characteristic_of_diagnosis": True,
    }  # fmt: skip
    fact.update(overrides)
    return fact


def _pass1(**overrides: Any) -> dict[str, Any]:
    out = {
        "rationale": "r", "evidence_quote": "creatinine 1.8-3.1 mg/dL",
        "evidence_value": "1.8-3.1 mg/dL", "evidence_population": "adults with TR",
        "variable_match": "exact", "condition_match": "exact", "population_match": "match",
        "evidence_type": "quantitative",
    }  # fmt: skip
    out.update(overrides)
    return out


# --- text checks --------------------------------------------------------------------------------


def test_case_mapping_and_source_pmcid() -> None:
    case = case_from_record(RECORD)
    assert case.narrative.startswith("A 75-year-old woman had dyspnea.")
    assert case.metadata["background_and_presentation"].startswith("A 75-year-old")
    assert source_pmcid("PMC123456_01") == "PMC123456"
    assert source_pmcid("test-urti-001") is None


def test_quote_found_tolerates_ellipses_and_spacing() -> None:
    text = "In 42 adults with severe TR, total bilirubin was 1.9 ± 0.8 mg/dL at baseline."
    assert quote_found("total  bilirubin was 1.9 ± 0.8 mg/dL", text)
    assert quote_found("In 42 adults … bilirubin was 1.9", text)
    assert not quote_found("bilirubin was 2.9 mg/dL", text)
    assert not quote_found("", text)


def test_count_value_matches_whole_numbers_only() -> None:
    assert count_value("pulse 80/min and 180 ms", "80") == 1
    assert count_value("creatinine 2.4 mg/dL", "2.4") == 1
    assert count_value("creatinine 12.45", "2.4") == 0


def test_check_redaction() -> None:
    original = "BP 100/60 mmHg. Creatinine 2.4 mg/dL. Pulse 80/min."
    span = "Creatinine 2.4 mg/dL"
    assert check_redaction(original, "BP 100/60 mmHg. Pulse 80/min.", span, "2.4") is None
    assert check_redaction(original, original, span, "2.4") == "span_still_present"
    assert (
        check_redaction(original, "BP 100/60 mmHg. Creat 2.4. Pulse 80/min.", span, "2.4")
        == "value_still_present"
    )
    assert (
        check_redaction(original, "BP 100/60 mmHg. Pulse 80/min, 99 kg.", span, "2.4")
        == "numbers_added"
    )


def test_check_facts_keeps_only_clean_askable_unique_values() -> None:
    text = case_from_record(RECORD).narrative
    facts = [
        ExtractedFact(**_fact()),
        ExtractedFact(**_fact(variable="heart rate", value="80", unit="/min", span="pulse 80/min",
                              category="vital_sign")),
        ExtractedFact(**_fact(variable="lesion size", value="80", span="pulse 80/min",
                              category="imaging_measurement")),
        ExtractedFact(**_fact(variable="blood pressure", value="120/80", span="BP 100/60 mmHg",
                              category="vital_sign")),
        ExtractedFact(**_fact(variable="potassium", span="potassium 4.1")),
    ]  # fmt: skip
    checked = check_facts(facts, text)
    assert [c.eligible for c in checked] == [True, True, False, False, False]
    assert [c.reject_reason for c in checked[2:]] == [
        "category:imaging_measurement", "value_not_in_span", "span_not_verbatim",
    ]  # fmt: skip


def test_question_wording_keeps_acronyms() -> None:
    assert question_for("Serum creatinine", "on admission") == (
        "What was the patient's serum creatinine on admission?"
    )
    assert question_for("CRP") == "What was the patient's CRP?"
    assert question_for("heart rate", past=False) == "What is the patient's heart rate?"


# --- grading and statistics ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "relevance", "usefulness"),
    [
        ({}, 3, 2),
        ({"condition_match": "related"}, 2, 2),
        ({"population_match": "partial"}, 2, 2),
        ({"condition_match": "unrelated"}, 1, 1),
        ({"evidence_type": "qualitative"}, 3, 1),
        ({"evidence_type": "qualitative", "condition_match": "unrelated"}, 1, 0),
        ({"variable_match": "absent", "evidence_type": "none"}, 1, 0),
        ({"variable_match": "absent", "condition_match": "related", "evidence_type": "none"}, 0, 0),
        ({"population_match": "mismatch"}, 0, 0),
    ],
)
def test_grades_from_facets(overrides: dict[str, Any], relevance: int, usefulness: int) -> None:
    out = Pass1Output(**_pass1(**overrides))
    assert relevance_grade(out) == relevance
    assert usefulness_grade(out, quote_ok=True) == usefulness


def test_invented_quote_zeroes_usefulness() -> None:
    assert usefulness_grade(Pass1Output(**_pass1()), quote_ok=False) == 0


def test_kappa_and_cluster_bootstrap() -> None:
    assert cohen_kappa([0, 1, 2, 3], [0, 1, 2, 3], weights="quadratic") == pytest.approx(1.0)
    assert cohen_kappa(["a", "b", "a", "b"], ["a", "a", "b", "b"]) == pytest.approx(0.0)
    est = cluster_bootstrap([("d1", 1.0), ("d1", 0.0), ("d2", 1.0), ("d3", 1.0)], seed=1)
    assert est.mean == pytest.approx(0.75)
    assert est.low is not None and est.high is not None and est.mean is not None
    assert est.low <= est.mean <= est.high


# --- retrieval wrappers -------------------------------------------------------------------------


def _doc(doc_id: str, text: str, **raw: Any) -> RetrievedDocument:
    return RetrievedDocument(
        source="europe_pmc", doc_id=doc_id, title=None, text=text, url=None, score=None, raw=raw
    )


def test_source_article_filter_drops_the_case_report() -> None:
    inner = FakeRetriever(
        "europe_pmc",
        [
            _doc("PMID:1", "the case report itself", pmid="1", pmcid="PMC123456"),
            _doc("PMID:2", "another study", pmid="2"),
            _doc("PMID:3", "same article found by PMID", pmid="999"),
        ],
    )
    wrapped = SourceArticleFilter(inner, pmcid="PMC123456", pmid="999")
    assert [d.doc_id for d in wrapped.search("q")] == ["PMID:2"]
    assert wrapped.excluded == ["PMID:1", "PMID:3"]
    assert wrapped.parameters()["source_article_filter"]["excluded"] == 2


def test_condition_blind_swaps_the_diagnosis_for_reference_terms() -> None:
    lq = LiteratureQuery(
        keywords="k", variable_terms=["creatinine"], condition_terms=["TR"],
        related_condition_terms=["heart failure"], context_terms=["elderly"],
    )  # fmt: skip
    blind = condition_blind(lq)
    assert "TR" not in blind.condition_terms
    assert "reference range" in blind.condition_terms
    assert blind.related_condition_terms == []
    assert blind.context_terms == []


# --- the pipeline end to end, offline -----------------------------------------------------------


RESOLVER_NO: dict[str, Any] = {
    "answerable_from_case": False, "answer": None, "evidence_spans": [], "reasoning": "r",
    "query_scope": "patient", "partial_facts": [],
}  # fmt: skip
BUILDER: dict[str, Any] = {
    "literature_query": "creatinine tricuspid regurgitation", "clinical_variable": "creatinine",
    "expected_answer_type": "numeric", "decline_reason": None,
    "variable_terms": ["creatinine"], "condition_terms": ["tricuspid regurgitation"],
    "related_condition_terms": [], "context_terms": [],
}  # fmt: skip
SYNTH: dict[str, Any] = {
    "answer": "Serum creatinine is 2.1 mg/dL.", "supporting_doc_ids": ["PMID:2"],
    "confidence": "medium", "consistent_with_case": True, "unanswerable": False,
    "value": "2.1", "unit": "mg/dL", "literature_range": "1.8-3.1 mg/dL (PMID:2)",
    "conflict": None,
}  # fmt: skip


def test_full_benchmark_offline(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "ws")
    case = case_from_record(RECORD)
    cases = {case.case_id: case}
    settings = make_settings()

    # extract
    llm = ScriptedLLM([{"facts": [_fact()]}])
    extracted = run_extract(
        ws, cases, [case.case_id], llm=llm, model="m", max_tokens=100, workers=1
    )
    assert extracted["eligible_facts"] == 1

    # redact (set A only; set B would need more cases)
    redacted_narrative = case.narrative.replace(" Serum creatinine was 2.4 mg/dL on admission.", "")
    llm.push(
        {"narrative": redacted_narrative, "background_and_presentation": RECORD[
            "background_and_presentation"], "removed": ["Serum creatinine was 2.4 mg/dL"],
         "qualitative_mentions_kept": []},
        RESOLVER_NO,
    )  # fmt: skip
    builder = ItemBuilder(
        cases, llm=llm, pipeline_llm=llm, settings=settings, redactor_model="m",
        redactor_max_tokens=100, lookup_pmid=lambda pmcid: "999",
    )  # fmt: skip
    run_redact(ws, cases, builder, set_a=1, set_b=0, workers=1)
    [item] = read_models(ws.items, Item)
    assert item.question == "What was the patient's serum creatinine on admission?"
    assert item.truth is not None and item.truth.value == "2.4"
    assert "2.4" not in item.case.narrative
    assert (item.source_pmcid, item.source_pmid) == ("PMC123456", "999")

    # run
    docs = [
        _doc("PMID:1", "Case report: creatinine 2.4 mg/dL.", pmid="999"),
        _doc("PMID:2", "In tricuspid regurgitation, creatinine 1.8-3.1 mg/dL in adults.",
             pmid="2"),
        _doc("PMID:3", "Cataract surgery outcomes in adults.", pmid="3"),
    ]  # fmt: skip
    llm.push(RESOLVER_NO, BUILDER, SYNTH)
    run_configs(
        ws, [item], [CONFIGS["current"]], llm=llm, base_settings=settings,
        retrievers=lambda s: [FakeRetriever("europe_pmc", docs)], workers=1,
    )  # fmt: skip
    [run] = read_models(ws.run_file("current"), RunRecord)
    assert run.status == "ok" and run.path == "literature"
    assert [d.doc_id for d in run.documents] == ["PMID:2", "PMID:3"]
    assert run.excluded_source_docs == ["PMID:1"]
    assert run.answer_value == "2.1"

    # judge: pass 1 for both documents and the answer check together, then pass 2
    off_topic = _pass1(variable_match="absent", condition_match="unrelated",
                       evidence_type="none", evidence_quote="", evidence_value="")  # fmt: skip
    llm.push(
        _pass1(),
        off_topic,
        {"reference_range": "0.6-1.2 mg/dL", "truth_category": "high", "answer_value": "2.1 mg/dL",
         "rationale": "r", "verdict": "same_category"},
        {"reference_range": "0.6-1.2 mg/dL", "truth_category": "high",
         "document_prediction": "1.8-3.1 mg/dL", "rationale": "r", "verdict": "within"},
    )  # fmt: skip
    judged = run_judge(ws, [item], ["current"], Judge(llm, "judge-model", 100), workers=1)
    assert judged["pass1:ok"] == 2 and judged["pass2:ok"] == 1 and judged["answer:ok"] == 1

    # report
    markdown, data = build_report(
        ws, [item], ["current"], judge_model="judge-model", second_judge_model=None,
        baseline="current", n_boot=50,
    )  # fmt: skip
    all_questions = data["all"]
    assert all_questions["u_hit"]["current"]["mean"] == 1.0
    assert all_questions["c_hit"]["current"]["mean"] == 1.0
    assert all_questions["mean_relevance"]["current"]["mean"] == pytest.approx(1.5)
    assert all_questions["answer_category"]["current"]["mean"] == 1.0
    assert all_questions["answer_close"]["current"]["mean"] == 0.0
    assert "## Cost" in markdown and "| current |" in markdown
