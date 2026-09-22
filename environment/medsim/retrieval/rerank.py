"""Optional LLM document selection: pick the candidates that state a value for this patient."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from medsim.llm.base import LLMClient
from medsim.llm.structured import call_structured
from medsim.models import ChatMessage, LiteratureQuery, LLMCallRecord, RetrievedDocument

SYSTEM_PROMPT = """\
You select literature for a patient simulator that must estimate one value for a patient.

From the numbered CANDIDATES, choose those that state a value, range, mean ± SD, median, or \
frequency of the TARGET VARIABLE in patients with the CONDITION (or a closely related one) and a \
population comparable to the PATIENT. Put the most informative first. Leave out animal or \
in-vitro studies, other age groups, and candidates that mention the variable without a number. \
Judge only the candidate text; do not use outside knowledge.
Return only a JSON object: {"reasoning": "<one or two sentences>", "selected_ids": ["C3", ...]}"""


class RerankOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reasoning: str
    selected_ids: list[str]


class LLMReranker:
    stage = "reranker"

    def __init__(
        self,
        llm: LLMClient,
        *,
        model: str | None = None,
        max_tokens: int = 4000,
        snippet_chars: int = 700,
    ) -> None:
        self.llm = llm
        self.model = model
        self.max_tokens = max_tokens
        self.snippet_chars = snippet_chars

    def build_messages(
        self, lq: LiteratureQuery, docs: Sequence[RetrievedDocument]
    ) -> list[ChatMessage]:
        candidates = "\n\n".join(
            f"[C{i + 1}] {doc.title or '(no title)'}\n{doc.text[: self.snippet_chars]}"
            for i, doc in enumerate(docs)
        )
        patient = ", ".join(p for p in (lq.patient_age_group, *lq.context_terms) if p) or "-"
        user = (
            f"TARGET VARIABLE: {', '.join(lq.variable_terms) or lq.keywords}\n"
            f"CONDITION: {', '.join(lq.condition_terms) or '-'}"
            f" (related: {', '.join(lq.related_condition_terms) or '-'})\n"
            f"PATIENT: {patient}\n\nCANDIDATES:\n{candidates}"
        )
        return [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=user),
        ]

    def select(
        self,
        lq: LiteratureQuery,
        docs: Sequence[RetrievedDocument],
        *,
        records: list[LLMCallRecord],
    ) -> list[int]:
        """Indices of the chosen candidates, best first (unknown or repeated ids dropped)."""
        output = call_structured(
            self.llm, stage="reranker", messages=self.build_messages(lq, docs),
            output_model=RerankOutput, temperature=0.0, max_tokens=self.max_tokens,
            model=self.model, records=records,
        )  # fmt: skip
        chosen: list[int] = []
        for raw_id in output.selected_ids:
            text = raw_id.strip().upper().lstrip("[").rstrip("]").removeprefix("C")
            if text.isdigit() and 0 < int(text) <= len(docs) and int(text) - 1 not in chosen:
                chosen.append(int(text) - 1)
        return chosen
