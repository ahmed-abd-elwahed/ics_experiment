"""Pydantic data contracts. ``EnvironmentResponse`` field names are the public API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceName = Literal["europe_pmc", "litsense", "openrouter_search"]
AnswerSource = Literal["case_study", "literature", "unanswerable"]
Confidence = Literal["high", "medium", "low"]
# "reranker" is the optional LLM document selection (MEDSIM_LLM_RERANK); extractor, redactor and
# judge are the retrieval benchmark's own calls (see bench/); "strategy" is an information
# gathering strategy's call in an experiment (see strategies/ at the project root).
StageName = Literal[
    "resolver",
    "query_builder",
    "synthesizer",
    "reranker",
    "extractor",
    "redactor",
    "judge",
    "strategy",
]
AgeGroup = Literal["neonate", "child", "adult"]


# --- Case study --------------------------------------------------------------------------------


class CaseStudy(BaseModel):
    case_id: str
    diagnosis: str
    narrative: str
    structured_findings: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Retrieval ---------------------------------------------------------------------------------


class RetrievedDocument(BaseModel):
    source: SourceName
    doc_id: str
    title: str | None
    text: str
    url: str | None
    score: float | None
    raw: dict[str, Any]


class LiteratureSearchResult(BaseModel):
    query: str
    documents: list[RetrievedDocument]
    per_source_counts: dict[str, int]
    errors: list[str] = Field(default_factory=list)
    latency_ms: float


# --- LLM ---------------------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None  # USD, as reported by OpenRouter's usage.cost


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage
    latency_ms: float
    finish_reason: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


CallPurpose = Literal["initial", "json_repair", "consistency_retry", "length_retry"]


class LLMCallRecord(BaseModel):
    stage: StageName
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: float
    attempt: int = 1
    purpose: CallPurpose = "initial"
    success: bool = True
    error: str | None = None
    finish_reason: str | None = None
    max_tokens: int | None = None
    cost_usd: float | None = None  # OpenRouter usage.cost for this call (search fees included)


# --- Stage outputs (strict JSON returned by the LLM) -------------------------------------------


class _StageOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ResolverOutput(_StageOutput):
    answerable_from_case: bool
    answer: str | None
    evidence_spans: list[str]
    reasoning: str
    # Extensions (see NOTES.md): needed for the §13 edge cases.
    query_scope: Literal["patient", "off_topic", "withheld"] = "patient"
    partial_facts: list[str] = Field(default_factory=list)


class QueryBuilderOutput(_StageOutput):
    literature_query: str | None
    clinical_variable: str | None
    expected_answer_type: Literal["numeric", "categorical", "descriptive"]
    decline_reason: str | None = None
    # Structured search terms; retrieval builds source-specific queries from these.
    variable_terms: list[str] = Field(default_factory=list)
    condition_terms: list[str] = Field(default_factory=list)
    related_condition_terms: list[str] = Field(default_factory=list)
    context_terms: list[str] = Field(default_factory=list)


class LiteratureQuery(BaseModel):
    """What to search for. ``keywords`` is the fallback for sources without a formulator."""

    keywords: str
    variable_terms: list[str] = Field(default_factory=list)
    condition_terms: list[str] = Field(default_factory=list)
    related_condition_terms: list[str] = Field(default_factory=list)
    context_terms: list[str] = Field(default_factory=list)
    expected_answer_type: Literal["numeric", "categorical", "descriptive"] = "descriptive"
    patient_age_group: AgeGroup | None = None  # from the case text; used by the population filter


class SynthesizerOutput(_StageOutput):
    answer: str
    supporting_doc_ids: list[str]
    confidence: Confidence
    consistent_with_case: bool
    unanswerable: bool
    # Extensions (see NOTES.md): needed for the ledger and range instantiation.
    value: str | None = None
    unit: str | None = None
    literature_range: str | None = None
    conflict: str | None = None


# --- Ledger ------------------------------------------------------------------------------------


class LedgerFact(BaseModel):
    case_id: str
    clinical_variable: str
    value: str
    unit: str | None
    source_doc_ids: list[str]
    answer: str
    query: str
    answer_source: Literal["case_study", "literature"]
    evidence: list[str] = Field(default_factory=list)
    confidence: Confidence = "high"


# --- Public response ---------------------------------------------------------------------------


class EnvironmentResponse(BaseModel):
    input_query: str
    output_answer: str
    literature_search: bool
    literature_search_result: LiteratureSearchResult | None
    retriever_parameters: dict[str, Any]
    used_llm: str
    answer_source: AnswerSource
    evidence: list[str]
    confidence: Confidence
    llm_calls: list[LLMCallRecord]
