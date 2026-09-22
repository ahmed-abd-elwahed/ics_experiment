"""Records written by each benchmark step, and the strict JSON the bench LLMs return."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from medsim.models import CaseStudy, LLMCallRecord

QuestionSet = Literal["A", "B"]  # A: hidden value from the case; B: value the case never states
Status = Literal["ok", "error"]

FactCategory = Literal[
    "vital_sign", "laboratory", "anthropometric", "imaging_measurement", "score_or_scale",
    "medication_or_dose", "other",
]  # fmt: skip
ELIGIBLE_CATEGORIES: tuple[str, ...] = ("vital_sign", "laboratory", "anthropometric")


class _LLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- extract ------------------------------------------------------------------------------------


class ExtractedFact(_LLMOutput):
    variable: str
    value: str
    unit: str | None
    timepoint: str | None
    span: str
    category: FactCategory
    askable_without_diagnosis: bool
    characteristic_of_diagnosis: bool


class ExtractorOutput(_LLMOutput):
    facts: list[ExtractedFact]


class CheckedFact(ExtractedFact):
    eligible: bool
    reject_reason: str | None = None


class CaseFacts(BaseModel):
    case_id: str
    diagnosis: str
    status: Status = "ok"
    error: str | None = None
    facts: list[CheckedFact] = Field(default_factory=list)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


# --- redact -------------------------------------------------------------------------------------


class RedactorOutput(_LLMOutput):
    narrative: str
    background_and_presentation: str
    removed: list[str]
    qualitative_mentions_kept: list[str]


class Truth(BaseModel):
    value: str
    unit: str | None
    span: str


class Item(BaseModel):
    item_id: str
    question_set: QuestionSet
    case_id: str
    diagnosis: str
    question: str
    variable: str
    category: str
    timepoint: str | None = None
    characteristic_of_diagnosis: bool | None = None
    truth: Truth | None = None
    case: CaseStudy  # redacted for set A, original for set B
    patient: str  # patient description shown to the judge (redacted for set A)
    source_pmcid: str | None = None
    source_pmid: str | None = None
    kept_qualitative: list[str] = Field(default_factory=list)
    removed_text: list[str] = Field(default_factory=list)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


class RejectedItem(BaseModel):
    item_id: str
    question_set: QuestionSet
    case_id: str
    variable: str
    reason: str
    detail: dict[str, Any] = Field(default_factory=dict)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


# --- run ----------------------------------------------------------------------------------------


class DocRecord(BaseModel):
    rank: int
    source: str
    doc_id: str
    title: str | None
    text: str  # exactly what Stage C saw (possibly truncated)
    full_text: str | None = None  # untruncated text, only when Stage C saw a truncated version
    url: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    journal: str | None = None
    pub_year: str | None = None
    pub_types: list[str] = Field(default_factory=list)


class RunRecord(BaseModel):
    item_id: str
    config: str
    question_set: QuestionSet
    status: Status
    error: str | None = None
    started_at: str
    wall_time_s: float
    path: str | None = None
    answer_source: str | None = None
    output_answer: str | None = None
    confidence: str | None = None
    evidence: list[str] = Field(default_factory=list)
    clinical_variable: str | None = None
    answer_value: str | None = None
    answer_unit: str | None = None
    literature_query: str | None = None
    documents: list[DocRecord] = Field(default_factory=list)
    excluded_source_docs: list[str] = Field(default_factory=list)
    failed_sources: list[str] = Field(default_factory=list)
    source_errors: list[str] = Field(default_factory=list)
    query_attempts: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)
    retrieval_cost_usd: float = 0.0  # search fees, search/rerank model tokens (0 for free APIs)
    # population_filtered, excerpts, llm_rerank, patient_age_group, as reported by the aggregator
    retrieval_notes: dict[str, Any] = Field(default_factory=dict)
    llm_cost_usd: dict[str, float] = Field(default_factory=dict)  # per pipeline stage


# --- judge --------------------------------------------------------------------------------------

VariableMatch = Literal["exact", "related", "absent"]
ConditionMatch = Literal["exact", "related", "unrelated"]
PopulationMatch = Literal["match", "partial", "unstated", "mismatch"]
EvidenceType = Literal["quantitative", "qualitative", "none"]
Category = Literal["low", "normal", "high"]
DocVerdict = Literal["within", "direction", "contradicts", "not_comparable"]
AnswerVerdict = Literal["close", "same_category", "different_category", "not_comparable"]


class Pass1Output(_LLMOutput):
    rationale: str
    evidence_quote: str
    evidence_value: str
    evidence_population: str
    variable_match: VariableMatch
    condition_match: ConditionMatch
    population_match: PopulationMatch
    evidence_type: EvidenceType


class Pass2Output(_LLMOutput):
    reference_range: str
    truth_category: Category
    document_prediction: str
    rationale: str
    verdict: DocVerdict


class AnswerOutput(_LLMOutput):
    reference_range: str
    truth_category: Category
    answer_value: str
    rationale: str
    verdict: AnswerVerdict


class Pass1Judgment(BaseModel):
    doc_key: str
    item_id: str
    doc_id: str
    source: str
    judge_model: str
    rubric: str
    status: Status
    error: str | None = None
    output: Pass1Output | None = None
    quote_ok: bool | None = None
    relevance: int | None = None
    usefulness: int | None = None
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


class Pass2Judgment(BaseModel):
    doc_key: str
    item_id: str
    doc_id: str
    source: str
    judge_model: str
    rubric: str
    truth_override: str | None = None  # set by the flipped-truth validation
    status: Status
    error: str | None = None
    output: Pass2Output | None = None
    correctness: int | None = None
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


class AnswerJudgment(BaseModel):
    item_id: str
    config: str
    answer_key: str
    judge_model: str
    rubric: str
    status: Status
    error: str | None = None
    output: AnswerOutput | None = None
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


# --- validate -----------------------------------------------------------------------------------

ControlKind = Literal["positive", "far_range", "off_topic", "veterinary"]


class ControlResult(BaseModel):
    item_id: str
    control: ControlKind
    judge_model: str
    rubric: str
    document: str
    expected: str
    passed: bool | None
    relevance: int | None = None
    usefulness: int | None = None
    correctness: int | None = None
    pass1: Pass1Output | None = None
    pass2: Pass2Output | None = None
    error: str | None = None
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


class FlipResult(BaseModel):
    doc_key: str
    item_id: str
    judge_model: str
    rubric: str
    original_verdict: str
    flipped_truth: str
    new_verdict: str | None
    passed: bool | None
    error: str | None = None
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


def calls_cost(calls: list[LLMCallRecord]) -> float:
    return sum(c.cost_usd or 0.0 for c in calls)
