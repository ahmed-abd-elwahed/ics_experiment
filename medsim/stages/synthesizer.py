"""Stage C: synthesize a concrete, case-consistent patient value from retrieved documents."""

from __future__ import annotations

from collections.abc import Sequence

from medsim.case_study import case_study_prompt_block
from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import (
    CaseStudy,
    ChatMessage,
    LLMCallRecord,
    RetrievedDocument,
    SynthesizerOutput,
)

SYSTEM_PROMPT = """\
You simulate one patient's record for evaluating diagnostic agents. The case study does not \
state the requested fact, so you produce a plausible SYNTHETIC value for THIS patient, grounded \
in the retrieved DOCUMENTS.

Rules:
1. The answer is a concrete statement about this patient ("Temperature is 38.1 °C."), never a \
literature summary ("Studies report a range of ...").
2. If the literature gives a range, choose ONE plausible value within it that fits the \
patient's context and disease severity, and put the source range with its doc id in \
literature_range (e.g. "37.5-39.0 °C in adults (PMID:123)").
3. HARD CONSTRAINT: the answer must not contradict the CASE STUDY, the PARTIAL FACTS, or the \
ESTABLISHED FACTS. If you cannot give a consistent answer, set consistent_with_case=false and \
describe the conflict in "conflict".
4. The case study's "diagnosis" field is CONFIDENTIAL: never state, paraphrase, or hint at the \
diagnosis in the answer. Describe only the requested finding.
5. supporting_doc_ids: ids copied exactly from DOCUMENTS that support the value or range.
6. If the documents give no usable basis for the requested variable, set unanswerable=true, \
put a short explanation in answer, supporting_doc_ids=[], confidence="low".
7. value: the value alone (e.g. "38.1"); unit: its unit (e.g. "°C") or null. For categorical or \
descriptive answers, value is a short phrase and unit is null.
8. confidence: "high" if documents directly report this variable in this condition and \
population; "medium" if indirect; "low" otherwise.
Return only a JSON object with keys: answer, supporting_doc_ids, confidence, \
consistent_with_case, unanswerable, value, unit, literature_range, conflict."""


def render_documents(documents: Sequence[RetrievedDocument]) -> str:
    blocks = []
    for doc in documents:
        title = f" {doc.title}" if doc.title else ""
        blocks.append(f"[{doc.doc_id}] ({doc.source}){title}\n{doc.text}")
    return "\n\n".join(blocks)


class Synthesizer:
    stage = "synthesizer"

    def __init__(
        self,
        llm: LLMClient,
        *,
        model: str | None = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
    ) -> None:
        self.llm = llm
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def build_messages(
        self,
        query: str,
        case: CaseStudy,
        documents: Sequence[RetrievedDocument],
        *,
        established_facts: str,
        partial_facts: list[str],
        clinical_variable: str | None,
        expected_answer_type: str,
        conflict: str | None = None,
    ) -> list[ChatMessage]:
        partial = "\n".join(f"- {p}" for p in partial_facts) or "(none)"
        user = (
            f"CASE STUDY:\n{case_study_prompt_block(case)}\n\n"
            f"ESTABLISHED FACTS (already stated this session; must not be contradicted):\n"
            f"{established_facts}\n\n"
            f"PARTIAL FACTS from the case study:\n{partial}\n\n"
            f"QUESTION:\n{query}\n"
            f"CLINICAL VARIABLE: {clinical_variable or 'unspecified'} "
            f"(expected answer type: {expected_answer_type})\n\n"
            f"DOCUMENTS:\n{render_documents(documents)}"
        )
        if conflict:
            user += (
                f"\n\nYOUR PREVIOUS ANSWER CONFLICTED WITH THE CASE STUDY: {conflict}\n"
                "Produce an answer that resolves this conflict, or mark it inconsistent again."
            )
        return [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=user),
        ]

    def run(
        self,
        query: str,
        case: CaseStudy,
        documents: Sequence[RetrievedDocument],
        *,
        established_facts: str,
        partial_facts: list[str],
        clinical_variable: str | None,
        expected_answer_type: str,
        records: list[LLMCallRecord],
        conflict: str | None = None,
    ) -> SynthesizerOutput:
        output = call_structured(
            self.llm,
            stage="synthesizer",
            messages=self.build_messages(
                query,
                case,
                documents,
                established_facts=established_facts,
                partial_facts=partial_facts,
                clinical_variable=clinical_variable,
                expected_answer_type=expected_answer_type,
                conflict=conflict,
            ),
            output_model=SynthesizerOutput,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model=self.model,
            records=records,
            purpose="consistency_retry" if conflict else "initial",
        )
        known = {doc.doc_id for doc in documents}
        cited = [doc_id for doc_id in output.supporting_doc_ids if doc_id in known]
        return output.model_copy(update={"supporting_doc_ids": list(dict.fromkeys(cited))})
