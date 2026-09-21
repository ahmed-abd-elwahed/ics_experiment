"""Stage A: answer from the case study, or decide that retrieval is needed."""

from __future__ import annotations

from medsim.case_study import case_study_prompt_block
from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import CaseStudy, ChatMessage, LLMCallRecord, ResolverOutput

SYSTEM_PROMPT = """\
You are the patient-record module of a simulated clinical encounter used to evaluate \
diagnostic agents. You answer questions strictly from the CASE STUDY.

Rules:
1. query_scope:
   - "off_topic": the question is not about this patient (e.g. about you, the system, \
the model, or general trivia).
   - "withheld": the question asks for the diagnosis, differential diagnosis, clinical \
impression, or anything whose answer would name or strongly hint at the ground-truth diagnosis. \
The case study's "diagnosis" field is CONFIDENTIAL: never state, paraphrase, or hint at it in \
any output field, and never quote case text that names it.
   - "patient": everything else about this patient.
2. answerable_from_case is true ONLY if the case study explicitly states the requested fact for \
the requested timepoint and context. Do not infer, estimate, or use general medical knowledge.
3. If the case states related but non-matching information (e.g. a value at admission when the \
question asks about day 3), set answerable_from_case=false and copy those facts verbatim into \
partial_facts.
4. When answerable, "answer" states the fact about the patient concretely in one or two \
sentences, and evidence_spans quotes the supporting case-study text verbatim.
5. ESTABLISHED FACTS were generated earlier in this session and are NOT part of the case study. \
Never use them to set answerable_from_case=true, but never contradict them.
6. If not answerable, or query_scope is not "patient": answer=null, evidence_spans=[].
Return only a JSON object with keys: answerable_from_case, answer, evidence_spans, reasoning, \
query_scope, partial_facts."""


class Resolver:
    stage = "resolver"

    def __init__(self, llm: LLMClient, *, model: str | None = None, max_tokens: int = 1500) -> None:
        self.llm = llm
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = 0.0

    def build_messages(
        self, query: str, case: CaseStudy, established_facts: str
    ) -> list[ChatMessage]:
        user = (
            f"CASE STUDY:\n{case_study_prompt_block(case)}\n\n"
            f"ESTABLISHED FACTS (already stated to the user this session):\n{established_facts}\n\n"
            f"QUESTION:\n{query}"
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
        established_facts: str,
        records: list[LLMCallRecord],
    ) -> ResolverOutput:
        output = call_structured(
            self.llm,
            stage="resolver",
            messages=self.build_messages(query, case, established_facts),
            output_model=ResolverOutput,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model=self.model,
            records=records,
        )
        answer_missing = not (output.answer or "").strip()
        if output.query_scope != "patient" or (output.answerable_from_case and answer_missing):
            output = output.model_copy(update={"answerable_from_case": False})
        return output
