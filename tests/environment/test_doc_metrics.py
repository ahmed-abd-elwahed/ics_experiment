"""Truth coverage and graded relevance of the retrieved documents, and the retrieval-only runs."""

from __future__ import annotations

from typing import Any

import pytest

from bench.doc_metrics import (
    CHANGES,
    IDEAL_DCG,
    DocJudgeOutput,
    DocJudgment,
    FrozenQuery,
    build_query,
    checked,
    doc_config,
    docs_key,
    judge_documents,
    ndcg,
    paired_difference,
    precision,
    retrieve_one,
    shuffled,
    summarize,
)
from bench.judge import Judge
from bench.schemas import DocRecord, Item, Truth
from medsim.errors import ConfigError
from medsim.models import CaseStudy, LiteratureQuery, RetrievedDocument
from tests.conftest import ScriptedLLM, make_settings
from tests.environment.test_environment import builder, resolver

CASE = CaseStudy(case_id="C1", diagnosis="Diabetic ketoacidosis",
                 narrative="A 24-year-old man with vomiting and Kussmaul breathing.")  # fmt: skip


def item() -> Item:
    return Item(
        item_id="A1", question_set="A", case_id="C1", diagnosis=CASE.diagnosis,
        question="What is the patient's serum potassium?", variable="serum potassium",
        category="lab", truth=Truth(value="5.9", unit="mmol/L", span="potassium 5.9 mmol/L"),
        case=CASE, patient="A 24-year-old man", source_pmcid="PMC1",
    )  # fmt: skip


def doc(rank: int, text: str) -> DocRecord:
    return DocRecord(rank=rank, source="europe_pmc", doc_id=f"D{rank}", title=f"T{rank}", text=text)


DOCS = [
    doc(1, "In DKA, admission potassium ranged from 5.5 to 6.5 mmol/L in most adults."),
    doc(2, "Potassium is measured in serum."),
    doc(3, "A review of cardiac surgery."),
]


def reply(**over: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "documents": [
            {"rank": 1, "grade": 2, "quote": "potassium ranged from 5.5 to 6.5 mmol/L"},
            {"rank": 2, "grade": 1, "quote": ""},
            {"rank": 3, "grade": 0, "quote": ""},
        ],
        "strict": True, "category": True, "coverage_rank": 1,
        "coverage_quote": "admission potassium ranged from 5.5 to 6.5 mmol/L", "rationale": "r",
    }  # fmt: skip
    return out | over


def test_ndcg_and_precision_against_eight_grade_two_documents() -> None:
    assert ndcg([2] * 8) == pytest.approx(1.0)
    assert ndcg([2] * 10) == pytest.approx(1.0)  # only the first eight count
    assert ndcg([0, 2]) == pytest.approx((2 / 1.5849625) / IDEAL_DCG, rel=1e-6)
    assert ndcg([2, 0]) > ndcg([0, 2])  # order matters
    assert ndcg([]) == 0.0
    assert (precision([2, 2, 1]), precision([2] * 8)) == (0.25, 1.0)


def test_quotes_are_checked_against_the_named_document() -> None:
    grades, strict, category, failures = checked(DocJudgeOutput(**reply()), DOCS)
    assert (grades, strict, category, failures) == ([2, 1, 0], True, True, 0)

    made_up = reply(documents=[{"rank": 1, "grade": 2, "quote": "potassium was 9 mmol/L"}],
                    coverage_rank=2)  # fmt: skip
    grades, strict, category, failures = checked(DocJudgeOutput(**made_up), DOCS)
    # an unquoted grade 2 counts as 1; a missing grade is 0; the quote is not in document 2
    assert (grades, strict, category, failures) == ([1, 0, 0], False, False, 2)

    only_category = reply(strict=False)
    assert checked(DocJudgeOutput(**only_category), DOCS)[1:3] == (False, True)
    strict_only = reply(category=False)  # strict implies the category level
    assert checked(DocJudgeOutput(**strict_only), DOCS)[1:3] == (True, True)


def test_the_judge_sees_the_truth_and_the_numbered_documents() -> None:
    llm = ScriptedLLM([reply()])
    judge = Judge(llm, "judge-model", 1000, sleep=lambda _: None)
    judged = judge_documents(judge, item(), "baseline", DOCS)
    assert judged.status == "ok" and (judged.strict, judged.grades) == (True, [2, 1, 0])
    user = llm.calls[0]["messages"][1].content
    assert 'TRUE VALUE: 5.9 mmol/L (case report: "potassium 5.9 mmol/L")' in user
    assert "[1] T1\nIn DKA" in user and "[3] T3" in user

    empty = judge_documents(judge, item(), "baseline", [])
    assert (empty.status, empty.grades, empty.strict, len(llm.calls)) == ("ok", [], False, 1)


def test_a_control_keeps_the_key_of_the_questions_own_documents() -> None:
    llm = ScriptedLLM([reply(strict=False, category=False, coverage_rank=None, coverage_quote="")])
    judge = Judge(llm, "judge-model", 1000, sleep=lambda _: None)
    own = [doc(1, "Unrelated text.")]
    control = judge_documents(
        judge, item(), "baseline", DOCS, control="shuffled", own_documents=own
    )
    assert (control.control, control.strict) == ("shuffled", False)
    assert control.docs_key == docs_key(own) != docs_key(DOCS)
    assert "In DKA" in llm.calls[0]["messages"][1].content  # judged on the other documents


def test_configurations_compose_on_the_baseline() -> None:
    base = make_settings()
    baseline = doc_config("baseline").settings(base)
    assert (baseline.rank_for_values, baseline.europe_pmc.page_size, baseline.max_documents) == (
        True, 50, 8
    )  # fmt: skip
    both = doc_config("q_natural+llm_select40").settings(base)
    assert (both.litsense.query_style, both.llm_rerank, both.rerank_candidates) == (
        "natural", True, 40
    )  # fmt: skip
    assert doc_config("q_gpt6luna").query_set == "gpt-6-luna"
    assert doc_config("baseline#2").settings(base) == baseline
    assert doc_config("llm_select20@fresh1").query_set == "fresh1"
    with pytest.raises(ConfigError, match="Unknown query set"):
        doc_config("baseline@nope")
    assert doc_config("epmc100").query_set == "base"
    with pytest.raises(ConfigError, match="Unknown change"):
        doc_config("q_natural+nonsense")
    for name in CHANGES:  # every change builds valid settings
        doc_config(name).settings(base)


def test_build_query_runs_stages_a_and_b() -> None:
    llm = ScriptedLLM([resolver(partial=["vomiting"]), builder(query="potassium DKA adults")])
    q = build_query(item(), llm=llm, settings=make_settings(), query_set="base")
    assert (q.status, q.path, q.partial_facts) == ("ok", "query", ["vomiting"])
    assert q.literature_query is not None and q.literature_query.keywords == "potassium DKA adults"
    assert q.literature_query.patient_age_group == "adult"

    llm.push(resolver(answerable=True, answer="It is 5.9."))
    assert build_query(item(), llm=llm, settings=make_settings(), query_set="base").path == (
        "case_study"
    )


class Fixed:
    name = "europe_pmc"

    def search(self, query: str, **params: Any) -> list[RetrievedDocument]:
        texts = {"PMC1": "The case itself: potassium 5.9 mmol/L.",
                 "PMC2": "In DKA potassium was 5.5-6.5 mmol/L at admission."}  # fmt: skip
        return [
            RetrievedDocument(
                source="europe_pmc",
                doc_id=pmc,
                title=pmc,
                text=text,
                url=None,
                score=1.0,
                raw={"pmcid": pmc, "abstractText": text},
            )
            for pmc, text in texts.items()
        ]

    def parameters(self) -> dict[str, Any]:
        return {}


def test_retrieve_one_returns_the_documents_without_the_source_article() -> None:
    query = FrozenQuery(
        item_id="A1", query_set="base", model="m", status="ok", path="query",
        literature_query=LiteratureQuery(keywords="potassium diabetic ketoacidosis",
                                         variable_terms=["potassium"],
                                         condition_terms=["diabetic ketoacidosis"]),
    )  # fmt: skip
    config = doc_config("no_excerpts+epmc_only")
    run = retrieve_one(item(), config, query, llm=ScriptedLLM(), base_settings=make_settings(),
                       retrievers=lambda s: [Fixed()])  # fmt: skip
    assert (run.status, run.path, run.config) == ("ok", "retrieval_only", "no_excerpts+epmc_only")
    assert [d.doc_id for d in run.documents] == ["PMC2"]
    assert run.excluded_source_docs == ["PMC1"]
    assert run.output_answer is None

    none = retrieve_one(item(), config, query.model_copy(update={"literature_query": None,
                                                                   "path": "case_study"}),
                        llm=ScriptedLLM(), base_settings=make_settings(),
                        retrievers=lambda s: [Fixed()])  # fmt: skip
    assert (none.path, none.documents) == ("case_study", [])


def test_shuffled_pairs_every_question_with_another() -> None:
    ids = [f"A{i}" for i in range(20)]
    pairs = shuffled(ids)
    assert sorted(pairs) == sorted(pairs.values()) == sorted(ids)
    assert all(a != b for a, b in pairs.items())
    assert shuffled(["A1"]) == {}


def judgment(item_id: str, grades: list[int], strict: bool) -> DocJudgment:
    return DocJudgment(item_id=item_id, config="c", docs_key="k", judge_model="j", rubric="d1",
                       status="ok", grades=grades, strict=strict, category=strict)  # fmt: skip


def test_summary_and_paired_difference() -> None:
    a = {"A1": judgment("A1", [2] * 8, True), "A2": judgment("A2", [0], False)}
    b = {"A1": judgment("A1", [2] * 8, True), "A2": judgment("A2", [2] * 8, True)}
    s = summarize(a, ["A1", "A2", "A3"])
    assert (s["questions"], s["missing"], s["strict"], s["ndcg"]) == (2, 1, 0.5, pytest.approx(0.5))
    d = paired_difference(a, b, "strict")
    assert (d["n"], d["mean"]) == (2, 0.5)
