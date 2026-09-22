from __future__ import annotations

from typing import Any

import httpx
import respx

from medsim.environment import (
    OFF_TOPIC_ANSWER,
    WITHHELD_ANSWER,
    MedicalEnvironment,
    build_retrievers,
)
from medsim.errors import RetrieverError
from medsim.models import CaseStudy, ChatMessage
from medsim.retrieval.base import Retriever
from tests.conftest import MODEL, ScriptedLLM, load_fixture, make_settings
from tests.environment.test_aggregator import FakeRetriever, _doc

TEMP_QUERY = "body temperature fever range common cold adults"
EPMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
LS_PASSAGES = "https://www.ncbi.nlm.nih.gov/research/litsense2-api/api/passages/"


def resolver(
    answerable: bool = False,
    answer: str | None = None,
    spans: list[str] | None = None,
    scope: str = "patient",
    partial: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "answerable_from_case": answerable, "answer": answer, "evidence_spans": spans or [],
        "reasoning": "test", "query_scope": scope, "partial_facts": partial or [],
    }  # fmt: skip


def builder(
    query: str | None = TEMP_QUERY,
    variable: str | None = "body temperature",
    kind: str = "numeric",
    decline: str | None = None,
) -> dict[str, Any]:
    return {
        "literature_query": query, "clinical_variable": variable,
        "expected_answer_type": kind, "decline_reason": decline,
    }  # fmt: skip


def synth(
    answer: str = "Temperature is 38.1 °C.",
    ids: list[str] | None = None,
    *,
    confidence: str = "medium",
    consistent: bool = True,
    unanswerable: bool = False,
    value: str | None = "38.1",
    unit: str | None = "°C",
    rng: str | None = "37.5-39.0 °C (PMID:42016338)",
    conflict: str | None = None,
) -> dict[str, Any]:
    return {
        "answer": answer, "supporting_doc_ids": ["PMID:42016338"] if ids is None else ids,
        "confidence": confidence, "consistent_with_case": consistent,
        "unanswerable": unanswerable, "value": value, "unit": unit,
        "literature_range": rng, "conflict": conflict,
    }  # fmt: skip


def docs_retrievers() -> list[FakeRetriever]:
    return [
        FakeRetriever("europe_pmc", [
            _doc("europe_pmc", "PMID:42016338", "Adults with colds: temperature 37.5-39.0 °C."),
            _doc("europe_pmc", "PMID:2", "Heart rate rises about 10 bpm per degree of fever."),
        ]),
        FakeRetriever("litsense", [
            _doc("litsense", "PMID:3#RESULTS-aa", "Resting heart rate was 70-100 bpm in adults."),
        ]),
    ]  # fmt: skip


def make_env(
    llm: ScriptedLLM, case: CaseStudy, retrievers: list[Retriever] | None = None
) -> MedicalEnvironment:
    return MedicalEnvironment(
        case_study=case,
        llm=llm,
        retrievers=retrievers if retrievers is not None else list(docs_retrievers()),
        settings=make_settings(),
    )


def user_prompt(call: dict[str, Any]) -> str:
    messages: list[ChatMessage] = call["messages"]
    return messages[-1].content


# --- the two main paths -------------------------------------------------------------------------


def test_case_study_hit_path(llm: ScriptedLLM, case: CaseStudy) -> None:
    fakes = docs_retrievers()
    env = make_env(llm, case, list(fakes))
    llm.push(resolver(True, "Her temperature at presentation was 37.9 °C.",
                      ["At presentation her temperature was 37.9 °C"]))  # fmt: skip

    response = env.query("What was her temperature at presentation?")

    assert response.answer_source == "case_study"
    assert response.output_answer == "Her temperature at presentation was 37.9 °C."
    assert response.literature_search is False
    assert response.literature_search_result is None
    assert response.evidence == ["At presentation her temperature was 37.9 °C"]
    assert response.confidence == "high"
    assert response.used_llm == MODEL
    assert [c.stage for c in response.llm_calls] == ["resolver"]
    assert response.retriever_parameters["path"] == "case_study"
    assert response.retriever_parameters["retrieval_performed"] is False
    assert all(f.queries == [] for f in fakes)
    # Diagnosis is visible to Stage A (per design decision) with an explicit refusal rule.
    assert case.diagnosis in user_prompt(llm.calls[0])
    assert "CONFIDENTIAL" in llm.calls[0]["messages"][0].content
    assert llm.calls[0]["temperature"] == 0.0


def test_retrieval_path_with_recorded_http(
    respx_mock: respx.MockRouter, llm: ScriptedLLM, case: CaseStudy
) -> None:
    epmc = respx_mock.get(url__startswith=EPMC_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("europe_pmc_search_core.json"))
    )
    litsense = respx_mock.get(url__startswith=LS_PASSAGES).mock(
        return_value=httpx.Response(200, json=load_fixture("litsense_passages.json"))
    )
    settings = make_settings()
    env = MedicalEnvironment(
        case_study=case, llm=llm, retrievers=build_retrievers(settings), settings=settings
    )
    partial = "At presentation her temperature was 37.9 °C"
    llm.push(resolver(False, partial=[partial]), builder(), synth())

    response = env.query("What is the patient's temperature on day 4?")

    assert response.answer_source == "literature"
    assert response.output_answer == "Temperature is 38.1 °C."
    assert response.literature_search is True
    result = response.literature_search_result
    assert result is not None
    assert result.query == TEMP_QUERY
    assert len(result.documents) == settings.max_documents
    assert result.per_source_counts == {"europe_pmc": 3, "litsense": 3}
    assert result.errors == []
    assert response.evidence == ["PMID:42016338", "literature range: 37.5-39.0 °C (PMID:42016338)"]
    assert response.confidence == "medium"
    assert [c.stage for c in response.llm_calls] == ["resolver", "query_builder", "synthesizer"]

    params = response.retriever_parameters
    assert params["literature_query"] == TEMP_QUERY
    assert params["sources"] == ["europe_pmc", "litsense"]
    assert params["per_source"]["europe_pmc"]["request_params"]["query"] == TEMP_QUERY
    assert params["per_source"]["litsense"]["endpoint"] == LS_PASSAGES
    assert params["max_documents"] == settings.max_documents
    assert epmc.call_count == litsense.call_count == 1

    builder_prompt, synth_prompt = user_prompt(llm.calls[1]), user_prompt(llm.calls[2])
    assert case.diagnosis in builder_prompt and partial in builder_prompt
    assert "[PMID:42016338]" in synth_prompt and partial in synth_prompt
    assert [c["temperature"] for c in llm.calls] == [0.0, 0.0, 0.2]


# --- failure and edge cases ---------------------------------------------------------------------


def test_both_sources_fail(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case, [
        FakeRetriever("europe_pmc", RetrieverError("europe_pmc", "timeout")),
        FakeRetriever("litsense", RetrieverError("litsense", "HTTP 503")),
    ])  # fmt: skip
    llm.push(resolver(), builder())
    response = env.query("What is the temperature on day 4?")
    assert response.answer_source == "unanswerable"
    assert response.literature_search is True
    assert response.literature_search_result is not None
    assert response.literature_search_result.documents == []
    assert len(response.literature_search_result.errors) == 2
    assert response.retriever_parameters["path"] == "all_sources_failed"
    assert len(response.llm_calls) == 2
    assert len(env.ledger) == 0


def test_one_source_fails_still_answers(llm: ScriptedLLM, case: CaseStudy) -> None:
    good = docs_retrievers()[0]
    env = make_env(
        llm, case, [good, FakeRetriever("litsense", RetrieverError("litsense", "HTTP 503"))]
    )
    llm.push(resolver(), builder(), synth())
    response = env.query("What is the temperature on day 4?")
    assert response.answer_source == "literature"
    assert response.literature_search_result is not None
    assert response.literature_search_result.errors == ["litsense: HTTP 503"]


def test_zero_results(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case, [FakeRetriever("europe_pmc", []), FakeRetriever("litsense", [])])
    llm.push(resolver(), builder())
    response = env.query("What is the temperature on day 4?")
    assert response.answer_source == "unanswerable"
    assert response.literature_search is True
    assert response.literature_search_result is not None
    assert response.literature_search_result.documents == []
    assert response.retriever_parameters["path"] == "no_documents"


def test_off_topic_spends_only_stage_a(llm: ScriptedLLM, case: CaseStudy) -> None:
    fakes = docs_retrievers()
    env = make_env(llm, case, list(fakes))
    llm.push(resolver(scope="off_topic"))
    response = env.query("What model are you?")
    assert response.answer_source == "unanswerable"
    assert response.output_answer == OFF_TOPIC_ANSWER
    assert response.literature_search is False
    assert [c.stage for c in response.llm_calls] == ["resolver"]
    assert all(f.queries == [] for f in fakes)


def test_diagnosis_question_is_withheld(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    llm.push(resolver(scope="withheld"))
    response = env.query("What is the diagnosis?")
    assert response.output_answer == WITHHELD_ANSWER
    assert case.diagnosis not in response.model_dump_json()
    assert len(response.llm_calls) == 1


def test_query_builder_declines(llm: ScriptedLLM, case: CaseStudy) -> None:
    fakes = docs_retrievers()
    env = make_env(llm, case, list(fakes))
    llm.push(resolver(), builder(None, None, "descriptive", "a name is not a clinical property"))
    response = env.query("What is the patient's name?")
    assert response.answer_source == "unanswerable"
    assert response.literature_search is False
    assert "not a clinical property" in response.output_answer
    assert [c.stage for c in response.llm_calls] == ["resolver", "query_builder"]
    assert all(f.queries == [] for f in fakes)


def test_malformed_llm_json_is_repaired(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    llm.push("{not json", resolver(True, "Blood pressure was 118/76 mmHg.", ["118/76 mmHg"]))
    response = env.query("What was her blood pressure?")
    assert response.answer_source == "case_study"
    assert [(c.purpose, c.success) for c in response.llm_calls] == [
        ("initial", False),
        ("json_repair", True),
    ]


def test_inconsistent_twice_becomes_unanswerable(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    llm.push(
        resolver(), builder(),
        synth(consistent=False, conflict="36.2 °C contradicts the documented fever"),
        synth(consistent=False, conflict="still contradicts"),
    )  # fmt: skip
    response = env.query("What is the temperature on day 4?")
    assert response.answer_source == "unanswerable"
    assert "still contradicts" in response.output_answer
    assert [c.purpose for c in response.llm_calls if c.stage == "synthesizer"] == [
        "initial",
        "consistency_retry",
    ]
    retry_prompt = user_prompt(llm.calls[-1])
    assert (
        "CONFLICTED WITH THE CASE STUDY: 36.2 °C contradicts the documented fever" in retry_prompt
    )
    assert len(env.ledger) == 0


def test_inconsistent_once_then_recovers(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    llm.push(resolver(), builder(), synth(consistent=False, conflict="too low"), synth())
    response = env.query("What is the temperature on day 4?")
    assert response.answer_source == "literature"
    assert len(response.llm_calls) == 4


def test_synthesizer_unanswerable_not_stored(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    declined = synth(
        "The documents do not report this.", [], unanswerable=True, value=None, unit=None, rng=None
    )
    llm.push(resolver(), builder(), declined)
    response = env.query("What is the temperature on day 4?")
    assert response.answer_source == "unanswerable"
    assert response.literature_search is True
    assert len(env.ledger) == 0


def test_uncited_answer_gets_low_confidence(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    llm.push(resolver(), builder(), synth(ids=["PMID:999999"], confidence="high"))
    response = env.query("What is the temperature on day 4?")
    assert response.answer_source == "literature"
    assert response.confidence == "low"
    assert "PMID:999999" not in response.evidence


# --- ledger coherence ---------------------------------------------------------------------------


def test_repeat_query_returns_ledger_value_without_llm(llm: ScriptedLLM, case: CaseStudy) -> None:
    fakes = docs_retrievers()
    env = make_env(llm, case, list(fakes))
    llm.push(resolver(), builder(), synth())
    first = env.query("What is the patient's temperature on day 4?")

    again = env.query("what was her temperature on day 4")
    assert again.output_answer == first.output_answer
    assert again.answer_source == "literature"
    assert again.llm_calls == []
    assert again.literature_search is False
    assert "ledger:temperature@day4" in again.evidence
    assert fakes[0].queries == [TEMP_QUERY]

    fahrenheit = env.query("What is the temperature on day 4 in Fahrenheit?")
    assert fahrenheit.output_answer == "Temperature is 38.1 °C. (100.6 °F)"
    assert fahrenheit.llm_calls == []


def test_paraphrase_caught_after_stage_b(llm: ScriptedLLM, case: CaseStudy) -> None:
    fakes = docs_retrievers()
    env = make_env(llm, case, list(fakes))
    llm.push(resolver(), builder(variable="body temperature on day 4"), synth())
    env.query("How warm is she on day 4?")

    llm.push(resolver(), builder(variable="body temperature"))
    response = env.query("What did the thermometer read on day 4?")
    assert response.output_answer == "Temperature is 38.1 °C."
    assert response.retriever_parameters["path"] == "ledger_hit_after_query_builder"
    assert [c.stage for c in response.llm_calls] == ["resolver", "query_builder"]
    assert fakes[0].queries == [TEMP_QUERY]
    assert "temperature@day4" in user_prompt(llm.calls[3])  # ledger injected into Stage A


def test_multi_part_query(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    llm.push(resolver(), builder(), synth())
    llm.push(
        resolver(),
        builder("heart rate tachycardia common cold adults", "heart rate"),
        synth("Heart rate is 88 bpm.", ["PMID:3#RESULTS-aa"], value="88", unit="bpm",
              rng="70-100 bpm (PMID:3#RESULTS-aa)"),
    )  # fmt: skip

    response = env.query("What are the patient's temperature and heart rate on day 4?")

    assert response.output_answer == "Temperature is 38.1 °C.\nHeart rate is 88 bpm."
    assert response.answer_source == "literature"
    params = response.retriever_parameters
    assert params["multi_part"] is True
    assert [s["query"] for s in params["sub_queries"]] == [
        "What are the patient's temperature on day 4?",
        "What are the patient's heart rate on day 4?",
    ]
    assert [s["literature_query"] for s in params["sub_queries"]] == [
        TEMP_QUERY,
        "heart rate tachycardia common cold adults",
    ]
    assert len(response.llm_calls) == 6
    result = response.literature_search_result
    assert result is not None
    assert result.query == f"{TEMP_QUERY} | heart rate tachycardia common cold adults"
    assert any(
        e.startswith("[What are the patient's heart rate on day 4?]") for e in response.evidence
    )
    # The first sub-answer is established before the second is resolved.
    assert "temperature@day4" in user_prompt(llm.calls[3])


def test_reset_clears_ledger(llm: ScriptedLLM, case: CaseStudy) -> None:
    env = make_env(llm, case)
    llm.push(resolver(), builder(), synth())
    env.query("What is the temperature on day 4?")
    assert len(env.ledger) == 1
    env.reset()
    assert len(env.ledger) == 0
    llm.push(resolver(), builder(), synth("Temperature is 37.8 °C.", value="37.8"))
    assert env.query("What is the temperature on day 4?").output_answer == "Temperature is 37.8 °C."


def test_shared_ledger_is_scoped_by_case_id(llm: ScriptedLLM, case: CaseStudy) -> None:
    question = "What is the temperature on day 4?"
    env_a = make_env(llm, case)
    llm.push(resolver(), builder(), synth())
    env_a.query(question)

    other_case = case.model_copy(update={"case_id": "other-case-002"})
    env_b = MedicalEnvironment(
        case_study=other_case, llm=llm, retrievers=list(docs_retrievers()),
        settings=make_settings(), ledger=env_a.ledger,
    )  # fmt: skip
    llm.push(resolver(), builder(), synth("Temperature is 36.9 °C.", value="36.9"))
    response_b = env_b.query(question)

    assert response_b.retriever_parameters["path"] == "literature"
    assert response_b.output_answer == "Temperature is 36.9 °C."
    assert len(response_b.llm_calls) == 3
    # Case A's fact is not offered to case B's prompts.
    assert "ESTABLISHED FACTS (already stated to the user this session):\n(none)" in user_prompt(
        llm.calls[3]
    )

    hit_a = env_a.query(question)
    assert hit_a.llm_calls == []
    assert hit_a.output_answer == "Temperature is 38.1 °C."
    assert hit_a.retriever_parameters["ledger_case_id"] == case.case_id

    env_b.reset()
    assert env_a.ledger.case_ids == [case.case_id]
    assert env_a.query(question).llm_calls == []


def test_structured_stage_b_terms_drive_source_specific_queries(
    respx_mock: respx.MockRouter, llm: ScriptedLLM, case: CaseStudy
) -> None:
    epmc = respx_mock.get(url__startswith=EPMC_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("europe_pmc_search_core.json"))
    )
    litsense = respx_mock.get(url__startswith=LS_PASSAGES).mock(
        return_value=httpx.Response(200, json=load_fixture("litsense_passages.json"))
    )
    # Open-access hits get their full text read (retrieval change 3, on by default); Europe PMC
    # answers with an error status when an article has none.
    fulltext = respx_mock.get(url__regex=r".*/europepmc/webservices/rest/PMC\d+/fullTextXML$").mock(
        return_value=httpx.Response(404)
    )
    settings = make_settings()
    env = MedicalEnvironment(
        case_study=case, llm=llm, retrievers=build_retrievers(settings), settings=settings
    )
    terms = builder() | {
        "variable_terms": ["body temperature", "fever"],
        "condition_terms": ["common cold", "upper respiratory tract infection"],
        "related_condition_terms": ["viral respiratory infection"],
        "context_terms": ["adults"],
    }
    llm.push(resolver(), terms, synth())

    response = env.query("What is the patient's temperature on day 4?")

    assert response.answer_source == "literature"
    epmc_query = epmc.calls[0].request.url.params["query"]
    assert epmc_query == (
        'TITLE_ABS:("body temperature" OR fever) AND '
        'TITLE_ABS:("common cold" OR "upper respiratory tract infection")'
    )
    assert litsense.calls[0].request.url.params["query"] == "body temperature common cold"

    per_source = response.retriever_parameters["per_source"]
    for source in ("europe_pmc", "litsense"):
        attempts = per_source[source]["query_attempts"]
        assert attempts[0]["level"] == "variable_and_condition"
        assert all("returned" in a for a in attempts)
    result = response.literature_search_result
    assert result is not None
    assert result.query.startswith("europe_pmc: TITLE_ABS:(")
    assert " | litsense: " in result.query
    assert response.retriever_parameters["literature_query"] == TEMP_QUERY
    assert "lexical term rerank" in response.retriever_parameters["ranking"]
    assert fulltext.called
    assert response.retriever_parameters["excerpts"]["full_text_used"] == 0
