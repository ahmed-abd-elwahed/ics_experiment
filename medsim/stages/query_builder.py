"""Stage B: describe what literature to search for, fusing the variable, diagnosis, and context."""

from __future__ import annotations

import json

from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import CaseStudy, ChatMessage, LLMCallRecord, QueryBuilderOutput

SYSTEM_PROMPT = """\
You plan a biomedical literature search. The results will be used to synthesize a plausible \
value for a clinical variable that a simulated patient's case study does not state. Retrieval \
code turns your term lists into source-specific queries (boolean title/abstract searches and \
short semantic phrases), so the terms must be the words that actually appear in article titles \
and abstracts.

Rules:
1. clinical_variable: a short name for what is asked (e.g. "body temperature", \
"serum lactate on day 3").
2. variable_terms: 1-5 ways the variable is written in the literature, most specific first: the \
standard name, common synonyms, unambiguous abbreviations, and the terms for abnormal values the \
DIAGNOSIS could cause. Examples: serum bilirubin -> ["total bilirubin", "serum bilirubin", \
"hyperbilirubinemia"]; heart rate -> ["heart rate", "tachycardia", "pulse rate"].
3. condition_terms: 1-5 names for the DIAGNOSIS as written in the literature: the exact \
diagnosis, standard synonyms, and unambiguous abbreviations of 3+ letters. No generic words \
such as "disease" or "patients".
4. related_condition_terms: 0-4 broader or closely related conditions whose literature would \
also inform the value: the parent category, a shared mechanism, or the organ-level syndrome \
(e.g. for tricuspid regurgitation: ["right heart failure", "congestive hepatopathy"]).
5. context_terms: 0-3 short patient-context words that change the expected value (e.g. \
"elderly", "pediatric", "pregnancy", "severe", "postoperative").
6. Every term is plain words only (at most 5 words): no quotes, parentheses, boolean operators, \
wildcards, or field tags.
7. literature_query: a concise fallback keyword query (4-10 words, no operators) fusing the \
variable, the DIAGNOSIS, and the most important context. Example: question "What is the \
patient's temperature?" with diagnosis "common cold" -> "body temperature fever common cold \
adults".
8. Set literature_query=null, all term lists to [], and explain in decline_reason when the \
question has no meaningful literature answer: identity or administrative details (name, \
address, insurance, contact details), personal preferences, or anything that is not a \
clinical, physiological, or epidemiological property of the patient.
9. expected_answer_type: "numeric" (a measurement), "categorical" (present/absent, \
positive/negative, grade), or "descriptive".
Return only a JSON object with keys: literature_query, clinical_variable, expected_answer_type, \
decline_reason, variable_terms, condition_terms, related_condition_terms, context_terms."""


class QueryBuilder:
    stage = "query_builder"

    def __init__(self, llm: LLMClient, *, model: str | None = None, max_tokens: int = 1200) -> None:
        self.llm = llm
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = 0.0

    def build_messages(
        self, query: str, case: CaseStudy, partial_facts: list[str]
    ) -> list[ChatMessage]:
        context = {
            "narrative": case.narrative,
            "structured_findings": case.structured_findings,
            "metadata": case.metadata,
        }
        partial = "\n".join(f"- {p}" for p in partial_facts) or "(none)"
        user = (
            f"QUESTION:\n{query}\n\n"
            f"DIAGNOSIS:\n{case.diagnosis}\n\n"
            f"PATIENT CONTEXT (from the case study):\n"
            f"{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
            f"PARTIAL FACTS the answer must respect:\n{partial}"
        )
        return [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=user),
        ]

    def run(
        self,
        query: str,
        case: CaseStudy,
        *,
        partial_facts: list[str],
        records: list[LLMCallRecord],
    ) -> QueryBuilderOutput:
        output = call_structured(
            self.llm,
            stage="query_builder",
            messages=self.build_messages(query, case, partial_facts),
            output_model=QueryBuilderOutput,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model=self.model,
            records=records,
        )
        if output.literature_query is not None and not output.literature_query.strip():
            output = output.model_copy(update={"literature_query": None})
        if output.literature_query is None:
            output = output.model_copy(
                update={
                    "variable_terms": [],
                    "condition_terms": [],
                    "related_condition_terms": [],
                    "context_terms": [],
                }
            )
        return output
