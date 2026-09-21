from __future__ import annotations

from medsim.models import LiteratureQuery, QueryBuilderOutput, RetrievedDocument
from medsim.retrieval.query_formulation import (
    RelevanceScorer,
    clean_term,
    clean_terms,
    europe_pmc_ladder,
    litsense_ladder,
    query_ladder,
    to_literature_query,
)

LQ = LiteratureQuery(
    keywords="serum bilirubin tricuspid regurgitation",
    variable_terms=["total bilirubin", "hyperbilirubinemia"],
    condition_terms=["tricuspid regurgitation"],
    related_condition_terms=["right heart failure"],
    context_terms=["elderly"],
    expected_answer_type="numeric",
)


def _doc(doc_id: str, text: str, title: str | None = None) -> RetrievedDocument:
    return RetrievedDocument(
        source="europe_pmc", doc_id=doc_id, title=title, text=text, url=None, score=None, raw={}
    )


def test_clean_term_removes_query_syntax() -> None:
    assert clean_term('"C-reactive protein" AND (CRP)') == "C-reactive protein CRP"
    assert clean_term("TITLE_ABS:bilirubin*") == "TITLE_ABS bilirubin"
    assert clean_terms(["Heart rate", "heart rate", "x", "", "pulse"]) == ["Heart rate", "pulse"]
    assert len(clean_terms([f"term {i}" for i in range(10)])) == 5


def test_europe_pmc_ladder_uses_title_abstract_synonym_groups() -> None:
    ladder = europe_pmc_ladder(LQ)
    assert [a.level for a in ladder] == [
        "variable_and_condition",
        "variable_and_related_condition",
        "variable_and_condition_any_field",
        "variable_reference_values",
    ]
    variable = 'TITLE_ABS:("total bilirubin" OR hyperbilirubinemia)'
    assert ladder[0].query == f'{variable} AND TITLE_ABS:("tricuspid regurgitation")'
    assert ladder[1].query == f'{variable} AND TITLE_ABS:("right heart failure")'
    assert ladder[2].query == (
        '("total bilirubin" OR hyperbilirubinemia) AND '
        '("tricuspid regurgitation" OR "right heart failure") AND HAS_ABSTRACT:y'
    )
    assert ladder[3].query == (
        f'{variable} AND TITLE_ABS:("reference range" OR "reference interval" OR '
        '"normal values" OR "healthy adults")'
    )


def test_europe_pmc_ladder_skips_related_level_without_related_terms() -> None:
    lq = LQ.model_copy(update={"related_condition_terms": []})
    assert "variable_and_related_condition" not in [a.level for a in europe_pmc_ladder(lq)]


def test_terms_cannot_inject_boolean_syntax() -> None:
    lq = LQ.model_copy(
        update={"variable_terms": ["bilirubin) OR (cancer"], "condition_terms": ["sepsis"]}
    )
    assert europe_pmc_ladder(lq)[0].query == (
        'TITLE_ABS:("bilirubin cancer") AND TITLE_ABS:(sepsis)'
    )


def test_litsense_ladder_uses_short_focused_phrases() -> None:
    assert [a.query for a in litsense_ladder(LQ)] == [
        "total bilirubin tricuspid regurgitation",
        "hyperbilirubinemia tricuspid regurgitation",
        "total bilirubin right heart failure",
        "total bilirubin reference range healthy adults",
    ]


def test_missing_terms_fall_back_to_keywords() -> None:
    bare = LiteratureQuery(keywords="fever common cold adults")
    for source in ("europe_pmc", "litsense", "some_new_source"):
        ladder = query_ladder(source, bare)
        assert [(a.level, a.query) for a in ladder] == [("keywords", "fever common cold adults")]
    assert [a.level for a in query_ladder("some_new_source", LQ)] == ["keywords"]


def test_scorer_prefers_variable_condition_and_value() -> None:
    scorer = RelevanceScorer(LQ)
    best = _doc("best", "Total bilirubin was 2.1 mg/dL in patients with tricuspid regurgitation.")
    var_cond = _doc("var_cond", "Bilirubin rises in tricuspid regurgitation.")
    var_related = _doc("var_related", "Hyperbilirubinemia is common in right heart failure.")
    cond_only = _doc("cond_only", "Grading tricuspid regurgitation severity.")
    unrelated = _doc("unrelated", "An unrelated abstract.")

    assert scorer.score(best) == 7.0
    assert scorer.score(var_cond) == 5.0  # "total bilirubin" also matches plain "bilirubin"
    assert scorer.score(var_related) == 4.0
    assert scorer.score(cond_only) == 2.0
    assert scorer.score(unrelated) == 0.0
    ranked = scorer.rank([unrelated, cond_only, var_related, best, var_cond])
    assert [d.doc_id for d in ranked] == [
        "best",
        "var_cond",
        "var_related",
        "cond_only",
        "unrelated",
    ]
    assert scorer.mentions_variable(var_related) and not scorer.mentions_variable(cond_only)


def test_scorer_is_inactive_without_terms() -> None:
    scorer = RelevanceScorer(LiteratureQuery(keywords="anything"))
    doc = _doc("a", "text")
    assert not scorer.active
    assert scorer.mentions_variable(doc)
    assert scorer.score(doc) == 0.0


def test_to_literature_query_maps_stage_b_output() -> None:
    output = QueryBuilderOutput(
        literature_query="serum sodium hyponatremia adrenal insufficiency",
        clinical_variable="serum sodium",
        expected_answer_type="numeric",
        variable_terms=["serum sodium", "hyponatremia"],
        condition_terms=["primary adrenal insufficiency", "Addison disease"],
    )
    lq = to_literature_query(output)
    assert lq.keywords == output.literature_query
    assert lq.variable_terms == ["serum sodium", "hyponatremia"]
    assert lq.condition_terms == ["primary adrenal insufficiency", "Addison disease"]
    assert lq.expected_answer_type == "numeric"
