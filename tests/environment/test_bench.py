from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bench.extract import check_facts, run_extract
from bench.items import ItemBuilder, all_set_b, question_for, run_redact
from bench.judge import Judge, answer_key, full_cases, run_judge, vote
from bench.pool import export_pool, run_pool, run_sample
from bench.report import build_report
from bench.run import CONFIGS, SourceArticleFilter, condition_blind, run_configs
from bench.schemas import (
    CaseFacts,
    ConsistencyJudgment,
    ControlResult,
    ExtractedFact,
    FlipResult,
    Item,
    RunRecord,
    SetCQuestionOutput,
)
from bench.set_c import SetCWriter, check_question, run_set_c
from bench.stats import cluster_bootstrap, cohen_kappa
from bench.text import (
    case_from_record,
    check_redaction,
    count_value,
    quote_found,
    source_pmcid,
)
from bench.validate import run_validate
from bench.workspace import JsonlWriter, Workspace, read_jsonl, read_models
from medsim.errors import ConfigError, LLMError
from medsim.models import LiteratureQuery, RetrievedDocument
from tests.conftest import ScriptedLLM, make_settings
from tests.environment.test_aggregator import FakeRetriever

RECORD = {
    "case_id": "PMC123456_01",
    "diagnosis": "Tricuspid valve regurgitation",
    "case_information": (
        "A 75-year-old woman had dyspnea. Exam: pulse 80/min, BP 100/60 mmHg, bibasal crackles. "
        "Serum creatinine was 2.4 mg/dL on admission."
    ),
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


# --- text checks --------------------------------------------------------------------------------


def test_case_mapping_and_source_pmcid() -> None:
    case = case_from_record(RECORD)
    assert case.narrative.startswith("A 75-year-old woman had dyspnea.")
    assert case.diagnosis == "Tricuspid valve regurgitation"
    assert case.metadata == {}
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


PANEL = ["judge-a", "judge-b", "judge-c"]  # the first is the main judge


@pytest.mark.parametrize(
    ("labels", "label", "resolution"),
    [
        (["exact", "exact", "same_category"], "exact", "majority"),
        (["same_category", "exact", "exact"], "exact", "majority"),  # the main judge is outvoted
        (["exact", "exact", "exact"], "exact", "unanimous"),
        (["different_category", "exact", "same_category"], "different_category",
         "tie_break_main_judge"),
        (["exact", None, "same_category"], "exact", "tie_break_main_judge"),  # 1-1 split
        ([None, "same_category", "exact"], "same_category", "tie_break_next_judge"),
        (["consistent", None, "consistent"], "consistent", "majority"),
        ([None, None, None], None, None),
    ],
)  # fmt: skip
def test_majority_vote(labels: list[str | None], label: str | None, resolution: str | None) -> None:
    result = vote(dict(zip(PANEL, labels, strict=True)))
    assert (result.label, result.resolution) == (label, resolution)
    assert list(result.votes) == PANEL  # every judge's own label is kept


MASKED: dict[str, Any] = {
    "reference_range": "0.6-1.2 mg/dL", "truth_category": "high", "answer_value": "2.1 mg/dL",
    "rationale": "r", "verdict": "same_category",
}  # fmt: skip


def _set_b_item() -> tuple[Item, Any]:
    case = case_from_record(RECORD)
    item = Item(
        item_id="B1", question_set="B", case_id=case.case_id, diagnosis=case.diagnosis,
        question="What is the patient's heart rate?", variable="heart rate",
        category="vital_sign", case=case, patient="A 75-year-old woman",
    )  # fmt: skip
    return item, case


CONSISTENT: dict[str, Any] = {
    "answer_value": "82/min", "conflicting_facts": [], "rationale": "r", "verdict": "consistent",
}  # fmt: skip


def test_judge_retries_failed_calls_and_unusable_replies() -> None:
    item, case = _set_b_item()
    waits: list[float] = []
    bad_label = {**CONSISTENT, "verdict": "probably"}  # not an allowed label
    llm = ScriptedLLM([
        LLMError("OpenRouter HTTP 400: provider error"),  # attempt 1: the call fails
        bad_label, "not json at all",  # attempt 2: invalid label, then the repair fails too
        CONSISTENT,  # attempt 3: usable
    ])  # fmt: skip
    judge = Judge(llm, "judge-model", 100, max_attempts=3, backoff_s=2.0, sleep=waits.append)
    judged = judge.consistency(item, case, "current", "Heart rate 82/min.")
    assert judged.status == "ok" and judged.output is not None
    assert judged.output.verdict == "consistent"
    assert waits == [2.0, 4.0]
    assert [c.success for c in judged.llm_calls] == [False, False, False, True]

    llm.push(*[LLMError("OpenRouter HTTP 503")] * 2)
    gave_up = Judge(llm, "judge-model", 100, max_attempts=2, sleep=waits.append).consistency(
        item, case, "current", "Heart rate 82/min."
    )
    assert gave_up.status == "error" and "503" in (gave_up.error or "")
    assert len(gave_up.llm_calls) == 2


def test_factual_consistency_sees_the_full_case_and_labels_answers(tmp_path: Path) -> None:
    case = case_from_record(RECORD)
    item = Item(
        item_id="B1", question_set="B", case_id=case.case_id, diagnosis=case.diagnosis,
        question="What is the patient's heart rate?", variable="heart rate",
        category="vital_sign", case=case, patient="A 75-year-old woman",
    )  # fmt: skip
    llm = ScriptedLLM([
        {"answer_value": "40/min", "conflicting_facts": ["pulse 80/min"], "rationale": "r",
         "verdict": "inconsistent"},
        {"answer_value": "82/min", "conflicting_facts": [], "rationale": "r",
         "verdict": "consistent"},
    ])  # fmt: skip
    judge = Judge(llm, "judge-model", 100)
    low = judge.consistency(item, case, "current", "Heart rate 40/min.")
    assert low.status == "ok" and low.output is not None and low.output.verdict == "inconsistent"
    prompt = llm.calls[0]["messages"][1].content
    assert "Tricuspid valve regurgitation" in prompt and "Serum creatinine was 2.4" in prompt
    high = judge.consistency(item, case, "current", "Heart rate 82/min.")
    assert high.output is not None and high.output.verdict == "consistent"
    assert "score" not in high.model_dump()

    ws = Workspace(tmp_path / "ws")
    run = RunRecord(
        item_id="B1", config="current", question_set="B", status="ok", started_at="t",
        wall_time_s=1.0, path="literature", answer_source="literature",
        output_answer="Heart rate 82/min.",
    )  # fmt: skip
    ws.run_file("current").parent.mkdir(parents=True)
    ws.run_file("current").write_text(run.model_dump_json() + "\n", encoding="utf-8")
    # three judges; the first one fails every attempt, the other two agree
    panel = [Judge(llm, model, 100, max_attempts=1) for model in PANEL]
    llm.push(LLMError("OpenRouter HTTP 503"), CONSISTENT, CONSISTENT)
    judged = run_judge(ws, [item], ["current"], panel, cases={}, workers=1)
    assert judged["todo"] == 3 and judged["factual_consistency [judge-a]:error"] == 1
    llm.push({**CONSISTENT, "verdict": "inconsistent"})  # the rerun retries only judge-a
    judged = run_judge(ws, [item], ["current"], panel, cases={}, workers=1)
    assert judged["todo"] == 1 and judged["factual_consistency [judge-a]:ok"] == 1
    stored = read_models(ws.consistency, ConsistencyJudgment)
    assert [(j.judge_model, j.status) for j in stored] == [
        ("judge-a", "error"), ("judge-b", "ok"), ("judge-c", "ok"), ("judge-a", "ok")
    ]  # fmt: skip
    assert {j.answer_key for j in stored} == {answer_key("B1", "current", "Heart rate 82/min.")}
    assert run_judge(ws, [item], ["current"], panel, cases={}, workers=1)["todo"] == 0
    # a second set B question whose run is missing still counts, without a label
    unrun = item.model_copy(update={"item_id": "B2"})
    _, data = build_report(
        ws, [item, unrun], ["current"], judge_models=PANEL, baseline="current", n_boot=20,
    )  # fmt: skip
    [scored] = [s for s in data["scores"] if s["item_id"] == "B1"]
    assert scored["votes"] == {"factual_consistency": {
        "judge-a": "inconsistent", "judge-b": "consistent", "judge-c": "consistent"
    }}  # fmt: skip
    assert scored["consistency"] == "consistent"
    assert scored["resolution"] == {"factual_consistency": "majority"}
    set_b = data["set_B"]
    assert set_b["fc_consistent"]["current"]["mean"] == 0.5
    assert set_b["fc_inconsistent"]["current"]["mean"] == 0.0
    assert set_b["fc_no_label"]["current"]["mean"] == 0.5
    assert data["not_run"] == {"current": 1}


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
        {"narrative": redacted_narrative, "removed": ["Serum creatinine was 2.4 mg/dL"],
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

    # judge: the answer against the hidden value (documents are not judged)
    # the three judges say exact, exact, same category: the voted label is exact
    llm.push({**MASKED, "verdict": "exact"}, {**MASKED, "verdict": "exact"}, MASKED)
    panel = [Judge(llm, model, 100) for model in PANEL]
    with pytest.raises(ConfigError, match="not in the case file"):
        run_judge(ws, [item], ["current"], panel, cases={}, workers=1)
    wrong = case.model_copy(update={"narrative": redacted_narrative})  # value removed
    with pytest.raises(ConfigError, match="does not state the hidden value"):
        full_cases([item], {case.case_id: wrong})
    judged = run_judge(ws, [item], ["current"], panel, cases=cases, workers=1)
    assert all(judged[f"masked_correctness [{model}]:ok"] == 1 for model in PANEL)
    assert [c["model"] for c in llm.calls[-3:]] == PANEL
    prompt = llm.calls[-1]["messages"][1].content
    assert "TRUE VALUE: 2.4 mg/dL" in prompt
    assert (
        "FULL CASE REPORT:" in prompt and "Serum creatinine was 2.4 mg/dL" in prompt
    )  # unredacted
    assert "DIAGNOSIS: Tricuspid valve regurgitation" in prompt

    # report
    markdown, data = build_report(
        ws, [item], ["current"], judge_models=PANEL, baseline="current", n_boot=50,
    )  # fmt: skip
    set_a = data["set_A"]
    assert set_a["mc_exact"]["current"]["mean"] == 1.0
    assert set_a["mc_same_category"]["current"]["mean"] == 0.0
    assert set_a["mc_different_category"]["current"]["mean"] == 0.0
    assert set_a["mc_not_comparable"]["current"]["mean"] == 0.0
    assert set_a["mc_no_label"]["current"]["mean"] == 0.0
    assert not any(key.startswith("fc_") for key in set_a)
    assert "## Cost" in markdown and "| current |" in markdown
    assert data["panel_agreement"]["masked correctness"]["resolution"] == {"majority": 1}
    assert "## Judge panel agreement" in markdown

    # validate: controls and the flipped truth, each judged by the whole panel (9 calls)
    exact = {**MASKED, "verdict": "exact"}
    far = {**MASKED, "verdict": "different_category"}
    llm.push(
        exact, exact, MASKED,  # control "true_value": voted exact -> passes
        far, MASKED, far,  # control "far_value": voted different category -> passes
        exact, far, far,  # flipped truth: voted different category -> the label changed
    )  # fmt: skip
    summary = run_validate(
        ws, [item], ["current"], panel, cases=cases, controls=1, flips=1, export_human=1,
        workers=1,
    )  # fmt: skip
    assert (summary["controls_run"], summary["flips_run"], summary["human_rows"]) == (2, 1, 1)
    controls = read_models(ws.controls, ControlResult)
    assert [(c.control, c.verdict, c.passed) for c in controls] == [
        ("true_value", "exact", True), ("far_value", "different_category", True)
    ]  # fmt: skip
    assert controls[0].votes == {"judge-a": "exact", "judge-b": "exact",
                                 "judge-c": "same_category"}  # fmt: skip
    [flip] = read_models(ws.flips, FlipResult)
    assert (flip.new_verdict, flip.resolution, flip.passed) == (
        "different_category",
        "majority",
        True,
    )
    assert "7.2" in llm.calls[-1]["messages"][1].content  # the case text states the moved value
    _, data = build_report(
        ws, [item], ["current"], judge_models=PANEL, baseline="current", n_boot=20,
    )  # fmt: skip
    assert data["validation"]["flipped_truth"] == {"changed": 1, "n": 1}


def test_pool_then_sample_offline(tmp_path: Path) -> None:
    case = case_from_record(RECORD)
    cases = {case.case_id: case}
    pool_ws = Workspace(tmp_path / "pool")
    facts = {case.case_id: CaseFacts(case_id=case.case_id, diagnosis=case.diagnosis,
                                     facts=check_facts([ExtractedFact(**_fact())],
                                                       case.narrative))}  # fmt: skip
    n_b = len(all_set_b(cases, facts))
    redacted = case.narrative.replace(" Serum creatinine was 2.4 mg/dL on admission.", "")
    llm = ScriptedLLM([
        {"facts": [_fact()]},
        {"narrative": redacted, "removed": ["Serum creatinine was 2.4 mg/dL"],
         "qualitative_mentions_kept": []},
        RESOLVER_NO,
        *[RESOLVER_NO] * (n_b - 1),
        RESOLVER_NO | {"query_scope": "withheld"},  # the last set B candidate is rejected
    ])  # fmt: skip
    builder = ItemBuilder(
        cases, llm=llm, pipeline_llm=llm, settings=make_settings(), redactor_model="m",
        redactor_max_tokens=100, lookup_pmid=lambda pmcid: "999",
    )  # fmt: skip
    built = run_pool(pool_ws, cases, llm=llm, builder=builder, extractor_model="m",
                     extractor_max_tokens=100, workers=1)  # fmt: skip
    assert built["candidates"] == 1 + n_b
    assert not llm.outputs

    facts_file, items_file = tmp_path / "facts.json", tmp_path / "items.json"
    all_file = tmp_path / "archive" / "all.json"
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(json.dumps([RECORD]), encoding="utf-8")
    exported = export_pool(
        pool_ws, cases, cases_file=cases_file, facts_file=facts_file, items_file=items_file,
        all_items_file=all_file, models={"extractor": "m"}, processing={"parallel_workers": 1},
        notes=["a note"],
    )  # fmt: skip
    assert (exported["set_a"], exported["set_b"], exported["rejected"]) == (1, 1, 1)
    assert exported["candidates_accepted"] == {"A": 1, "B": n_b - 1}
    data = json.loads(items_file.read_text(encoding="utf-8"))
    archive = json.loads(all_file.read_text(encoding="utf-8"))
    assert len(archive["items"]) == n_b and len(archive["rejected"]) == 1
    assert archive["metadata"]["statistics"]["questions"] == {"A": 1, "B": n_b - 1}
    assert data["rejected"] == [] and data["metadata"]["selection"]["cases_without_set_a"] == []
    assert data["format"] == "bench-pool-items" and "llm_calls" not in data["items"][0]
    meta = data["metadata"]
    assert meta["notes"] == ["a note"] and meta["processing"] == {"parallel_workers": 1}
    assert meta["source_dataset"]["sha256"] and meta["prompts"]["redactor"].startswith("You")
    assert meta["statistics"]["questions"] == {"A": 1, "B": 1}
    assert archive["metadata"]["statistics"]["rejected"]["B"] == {"stage_a_scope_withheld": 1}
    usage = meta["statistics"]["llm_usage"]
    assert sum(u["calls"] for u in usage.values()) == 2 + n_b  # redactor + resolver calls
    facts_meta = json.loads(facts_file.read_text(encoding="utf-8"))["metadata"]
    assert facts_meta["statistics"]["eligible_facts"] == 1
    assert facts_meta["companion_files"] == [str(items_file), str(all_file)]
    assert data["items"][0]["source_pmid"] == "999"

    # a rerun builds nothing new
    assert run_pool(
        pool_ws,
        cases,
        llm=llm,
        builder=builder,
        extractor_model="m",
        extractor_max_tokens=100,
        workers=1,
    )["items"] == {"already_done": 1 + n_b}

    ws = Workspace(tmp_path / "ws")
    summary = run_sample(ws, facts_file=facts_file, items_file=items_file, set_a=5, set_b=5)
    assert summary["A"]["accepted"] == 1 and summary["B"]["accepted"] == 1
    sampled = read_models(ws.items, Item)
    assert sampled[0].item_id == "A:PMC123456_01:serum_creatinine"
    assert "Serum creatinine was 2.4" not in sampled[0].case.narrative
    with pytest.raises(ConfigError, match="already has questions"):
        run_sample(ws, facts_file=facts_file, items_file=items_file, set_a=1, set_b=1)
    full = run_sample(Workspace(tmp_path / "ws2"), facts_file=facts_file, items_file=all_file,
                      set_a=5, set_b=5)  # fmt: skip
    assert full["A"]["accepted"] == 1 and full["B"]["accepted"] + full["B"]["rejected"] >= 1


# --- set C: information the case states -----------------------------------------------------------


SET_C_QUESTION: dict[str, Any] = {
    "question": "What was the patient's pulse on examination?", "variable": "pulse",
    "answer": "80", "unit": "/min", "timepoint": "on examination", "span": "pulse 80/min",
    "answer_type": "numeric", "category": "vital_sign",
}  # fmt: skip


def test_set_c_question_checks() -> None:
    case = case_from_record(RECORD)
    good = SetCQuestionOutput(**SET_C_QUESTION)
    assert check_question(good, case) is None
    bad_span = good.model_copy(update={"span": "pulse 88/min"})
    assert check_question(bad_span, case) == "the span is not verbatim in the case"
    named = good.model_copy(update={"question": "Pulse in tricuspid valve regurgitation?"})
    assert check_question(named, case) == "the question names the diagnosis"
    leaked = good.model_copy(update={"question": "Was the pulse 80/min?"})
    assert check_question(leaked, case) == "the question contains the answer"


def test_set_c_end_to_end_without_retrieval(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "ws")
    case = case_from_record(RECORD)
    second = case.model_copy(update={"case_id": "PMC999999_01"})
    llm = ScriptedLLM([
        {**SET_C_QUESTION, "span": "pulse 88/min"}, SET_C_QUESTION,  # rewritten once, accepted
        {**SET_C_QUESTION, "question": "What was the serum creatinine?", "variable":
         "serum creatinine", "answer": "2.4", "unit": "mg/dL", "timepoint": "on admission",
         "span": "Serum creatinine was 2.4 mg/dL", "category": "laboratory"},
    ])  # fmt: skip
    writer = SetCWriter(llm, model="writer", max_tokens=100)
    cases = {case.case_id: case, second.case_id: second}
    assert run_set_c(ws, cases, writer, workers=1)["accepted"] == 2
    items = read_models(ws.items, Item)
    assert [i.question_set for i in items] == ["C", "C"] and items[0].case == case  # unredacted
    assert items[0].truth is not None and items[0].truth.span == "pulse 80/min"
    assert len(items[0].llm_calls) == 2  # the rejected question and its rewrite

    # the environment answers the first from the case; the second finds no answer, no search
    resolved = {**RESOLVER_NO, "answerable_from_case": True, "answer": "Pulse 80/min.",
                "evidence_spans": ["pulse 80/min"]}  # fmt: skip
    llm.push(resolved, RESOLVER_NO, BUILDER)
    run_configs(
        ws, items, [CONFIGS["case_information"]], llm=llm, base_settings=make_settings(),
        retrievers=lambda s: pytest.fail("set C must not search"), workers=1,
    )  # fmt: skip
    runs = {r.item_id: r for r in read_models(ws.run_file("case_information"), RunRecord)}
    assert runs[items[0].item_id].path == "case_study"
    assert runs[items[1].item_id].path == "no_documents" and not runs[items[1].item_id].documents
    assert {c["model"] for c in llm.calls[-3:]} == {"deepseek/deepseek-v4.1-flash:batch"}

    # the one answer gets both metrics from all three judges
    llm.push(*[{**MASKED, "verdict": "exact", "truth_category": "normal"}] * 3,
             *[CONSISTENT] * 3)  # fmt: skip
    panel = [Judge(llm, model, 100) for model in PANEL]
    judged = run_judge(ws, items, ["case_information"], panel, cases={}, workers=1)
    assert judged["todo"] == 6
    prompts = [c["messages"][0].content for c in llm.calls[-6:]]
    assert all("which the simulator could read" in p for p in prompts[:3])
    assert all("from the patient's case report, which" in p for p in prompts[3:])
    _, data = build_report(
        ws, items, ["case_information"], judge_models=PANEL, baseline="case_information",
        n_boot=20,
    )  # fmt: skip
    set_c = data["set_C"]
    assert set_c["mc_c_exact"]["case_information"]["mean"] == 0.5
    assert set_c["mc_c_no_label"]["case_information"]["mean"] == 0.5
    assert set_c["fc_c_consistent"]["case_information"]["mean"] == 0.5
    assert "set_A" not in data and "set_B" not in data


def test_jsonl_records_with_unicode_line_separators_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    writer = JsonlWriter(path)
    texts = ["first\u2028line", "next\x85line", "plain"]
    for text in texts:
        writer.write({"text": text})
    assert [r["text"] for r in read_jsonl(path)] == texts
