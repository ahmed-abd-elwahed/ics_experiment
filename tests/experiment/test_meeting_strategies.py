"""The four strategies of Meeting 63: what each asks, when it stops, and what it records."""

from __future__ import annotations

from typing import Any

from strategies import CaseContext, build_strategy, describe_strategies
from strategies.base import StrategySession
from strategies.common import DIAGNOSE, RankedEntry, ranked
from tests.conftest import ScriptedLLM, make_settings

DDX = {
    "differential": [
        {"diagnosis": "Infective endocarditis", "probability": 0.6},
        {"diagnosis": "Rheumatic fever", "probability": 0.2},
    ]
}


def session(llm: ScriptedLLM, name: str, limit: int | None = 4, **params: Any) -> StrategySession:
    strategy = build_strategy(name, params, llm=llm, settings=make_settings())
    return strategy.new_session(CaseContext(max_iterations=limit))


def system_prompts(llm: ScriptedLLM) -> list[str]:
    return [call["messages"][0].content.split("\n\n")[1][:32] for call in llm.calls]


def test_all_four_are_registered_with_default_params() -> None:
    names = {entry["name"] for entry in describe_strategies()}
    assert {"hypothesis", "knowledge", "channel", "sequence"} <= names


def test_hypothesis_asks_updates_and_stops_on_a_clear_leader(llm: ScriptedLLM) -> None:
    s = session(llm, "hypothesis")
    llm.push({"question": "What is the complaint?", "separates": [], "rationale": "Start."})
    first = s.next_question()
    assert first is not None and len(first.llm_calls) == 1  # nothing to update yet
    s.remember(first.text, "Fever and a new murmur.")

    open_differential = {
        "hypotheses": [
            {"diagnosis": "Endocarditis", "probability": 3, "evidence_for": "murmur"},
            {"diagnosis": "Rheumatic fever", "probability": 2},
        ]
    }
    llm.push(open_differential, {"question": "Any IV drug use?", "separates": ["Endocarditis"]})
    second = s.next_question()
    assert second is not None and len(second.llm_calls) == 2
    assert [h["probability"] for h in second.trace["differential"]] == [0.6, 0.4]  # renormalised
    assert "Endocarditis (p=0.60)" in llm.calls[-1]["messages"][1].content
    s.remember(second.text, "Yes.")

    llm.push({"hypotheses": [{"diagnosis": "Endocarditis", "probability": 0.9},
                             {"diagnosis": "Rheumatic fever", "probability": 0.1}]})  # fmt: skip
    assert s.next_question() is None  # 0.9 >= accept, lead 0.8 >= margin

    llm.push(DDX)
    diagnosis = s.final_diagnosis()
    assert diagnosis is not None
    assert [d.name for d in diagnosis.differential] == ["Infective endocarditis", "Rheumatic fever"]
    assert len(diagnosis.llm_calls) == 2  # the stopping update is saved with the diagnosis
    assert diagnosis.trace["satisficing"] is True
    assert llm.calls[-1]["messages"][0].content == DIAGNOSE


def test_knowledge_stops_when_a_pattern_is_complete(llm: ScriptedLLM) -> None:
    s = session(llm, "knowledge")
    s.remember("What is the complaint?", "Fever.")
    gap = {"name": "Febrile illness", "present": ["fever"], "missing": ["duration"]}
    llm.push({"findings": ["fever"], "patterns": [gap], "basics_covered": True},
             {"question": "How long has the fever lasted?", "fills": "duration"})  # fmt: skip
    question = s.next_question()
    assert question is not None and question.trace["fills"] == "duration"
    assert "Do not name or imply a diagnosis" in llm.calls[-1]["messages"][0].content
    s.remember(question.text, "Two weeks.")

    done = {"name": "Prolonged fever", "present": ["fever", "two weeks"], "missing": []}
    llm.push({"findings": [], "patterns": [done], "basics_covered": False},
             {"question": "What are the vital signs?"})  # fmt: skip
    assert s.next_question() is not None  # complete, but the basics are not covered
    s.remember("What are the vital signs?", "Normal.")
    llm.push({"findings": [], "patterns": [done], "basics_covered": True})
    assert s.next_question() is None


def test_channel_confines_questions_and_opens_the_exam_when_unsure(llm: ScriptedLLM) -> None:
    s = session(llm, "channel")  # 4 questions over 2 channels: 2 each
    llm.push({"question": "What is the heart rate?"}, {"kind": "exam"},
             {"question": "What is the complaint?"}, {"kind": "interview"})  # fmt: skip
    first = s.next_question()
    assert first is not None and first.text == "What is the complaint?"
    assert first.trace["channel"] == "interview"
    assert first.trace["rejected"] == [
        {"channel": "interview", "question": "What is the heart rate?", "kind": "exam"}
    ]
    assert "was rejected: it belongs to the exam channel" in llm.calls[2]["messages"][1].content
    s.remember(first.text, "Chest pain.")
    llm.push({"question": "When did it start?"}, {"kind": "interview"})
    second = s.next_question()
    assert second is not None
    s.remember(second.text, "An hour ago.")

    llm.push({"diagnosis": "Myocardial infarction", "confidence": 0.5},
             {"question": "What is the blood pressure?"}, {"kind": "exam"})  # fmt: skip
    third = s.next_question()
    assert third is not None and third.trace["channel"] == "exam"
    assert third.trace["assessments"][0]["confidence"] == 0.5
    assert "the physical examination" in llm.calls[-2]["messages"][0].content
    s.remember(third.text, "90/60.")
    llm.push({"question": "", "nothing_left": True})
    assert s.next_question() is None  # the last channel has nothing left: no assessment needed
    llm.push(DDX)
    diagnosis = s.final_diagnosis()
    assert diagnosis is not None
    assert "Working diagnosis after the interview" in llm.calls[-1]["messages"][1].content


def test_channel_stops_after_the_interview_when_confident(llm: ScriptedLLM) -> None:
    s = session(llm, "channel", questions_per_channel=1)
    llm.push({"question": "What is the complaint?"}, {"kind": "interview"})
    question = s.next_question()
    assert question is not None
    s.remember(question.text, "Crushing chest pain radiating to the left arm.")
    llm.push({"diagnosis": "Myocardial infarction", "confidence": 0.85})
    assert s.next_question() is None


def test_sequence_passes_through_its_three_phases(llm: ScriptedLLM) -> None:
    s = session(llm, "sequence")  # 4 questions: 1 opening, 2 refining, 1 final
    llm.push({"question": "What is the complaint?"})
    q1 = s.next_question()
    assert q1 is not None and q1.trace == {"phase": "init", "candidates": []}
    s.remember(q1.text, "Fever.")

    llm.push({"candidates": ["Endocarditis", "Pneumonia", "Malaria"]}, {"question": "Any cough?"})
    q2 = s.next_question()
    assert q2 is not None and q2.trace["phase"] == "refine"
    assert len(q2.llm_calls) == 2  # the draft is not pruned before a new answer arrives
    s.remember(q2.text, "No.")

    llm.push({"candidates": ["Endocarditis", "Malaria", "Typhoid"]}, {"question": "Any travel?"})
    q3 = s.next_question()
    assert q3 is not None and q3.trace == {
        "phase": "refine",
        "candidates": ["Endocarditis", "Malaria", "Typhoid"],
    }
    s.remember(q3.text, "No.")

    llm.push({"candidates": ["Endocarditis", "Typhoid", "Malaria"]}, {"question": "A murmur?"})
    q4 = s.next_question()  # the refinement budget is used: final phase
    assert q4 is not None and q4.trace["phase"] == "final"
    assert "Phase 3" in llm.calls[-1]["messages"][0].content
    s.remember(q4.text, "Yes, a new murmur.")

    llm.push({"diagnosis": "Endocarditis", "settled": True})
    assert s.next_question() is None
    llm.push(DDX)
    diagnosis = s.final_diagnosis()
    assert diagnosis is not None and diagnosis.trace["verdict"]["settled"] is True
    assert "Endocarditis (settled)" in llm.calls[-1]["messages"][1].content


def test_sequence_goes_to_the_final_phase_once_the_list_is_narrow(llm: ScriptedLLM) -> None:
    s = session(llm, "sequence", limit=8)  # 2 opening questions
    s.remember("What is the complaint?", "Fever.")
    s.remember("For how long?", "Two weeks.")
    llm.push({"candidates": ["Endocarditis", "Typhoid"]}, {"question": "A murmur?"})
    question = s.next_question()
    assert question is not None and question.trace["phase"] == "final"


def test_ranked_orders_by_probability_and_drops_repeats() -> None:
    entries = [
        RankedEntry(diagnosis="  Malaria ", probability=0.2),
        RankedEntry(diagnosis="Typhoid", probability=0.5),
        RankedEntry(diagnosis="malaria", probability=0.9),
        RankedEntry(diagnosis="", probability=0.9),
        RankedEntry(diagnosis="Dengue", probability=1.7),
    ]
    assert [(d.name, d.probability) for d in ranked(entries)] == [
        ("Dengue", 1.0), ("Typhoid", 0.5), ("Malaria", 0.2)
    ]  # fmt: skip
