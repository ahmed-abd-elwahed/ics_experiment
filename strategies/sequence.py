"""Sequence-based collection (Meeting 63, slide 12).

Three phases in a fixed order: initialization of the diagnosis, refinement of the diagnosis,
and defining the final diagnosis. Each phase has its own goal and its share of the questions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from medsim.models import LLMCallRecord
from strategies.base import CaseContext, Diagnosis, Question
from strategies.common import (
    CLINICIAN,
    QUESTION_RULES,
    LLMSession,
    LLMStrategy,
    LLMStrategyParams,
)

Phase = Literal["init", "refine", "final"]

GOALS: dict[Phase, str] = {
    "init": (
        "Phase 1, initialization of the diagnosis. Ask a broad opening question: the "
        "presenting complaint, then its history. Do not test a diagnosis yet."
    ),
    "refine": (
        "Phase 2, refinement of the diagnosis. Ask the question whose answer would rule out "
        "one of the candidate diagnoses."
    ),
    "final": (
        "Phase 3, defining the final diagnosis. Ask for the one finding that would confirm or "
        "exclude the leading candidate."
    ),
}

ASK = f"""\
{CLINICIAN}

You work in three phases: initialization, refinement, final diagnosis. {{goal}}

{QUESTION_RULES}

Return only a JSON object with keys question and rationale (one sentence)."""

DRAFT = f"""\
{CLINICIAN}

From the opening answers, draft the first differential: at most 5 candidate diagnoses, most \
likely first.

Return only a JSON object with the key candidates, a list of diagnosis names."""

PRUNE = f"""\
{CLINICIAN}

Refine the candidate diagnoses with the newest answer: remove the ones it rules out, reorder \
the rest with the most likely first, and add a diagnosis only if the answer points to one that \
is missing. Keep at most 5.

Return only a JSON object with the key candidates, a list of diagnosis names."""

SETTLE = f"""\
{CLINICIAN}

You asked for the finding that would confirm or exclude your leading candidate. Decide: name \
the diagnosis you now hold, and say whether it is settled (true) or still open (false).

Return only a JSON object with keys diagnosis and settled."""


class PhaseQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    rationale: str = ""


class Candidates(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidates: list[str]


class Verdict(BaseModel):
    model_config = ConfigDict(extra="ignore")

    diagnosis: str
    settled: bool


class SequenceParams(LLMStrategyParams):
    # Shares of the question budget (the iteration limit, or ``budget`` without one). The
    # refinement phase gets the rest, and ends early when ``narrow_to`` candidates remain.
    opening_share: float = Field(default=0.25, gt=0.0, lt=1.0)
    final_share: float = Field(default=0.25, gt=0.0, lt=1.0)
    narrow_to: int = Field(default=2, ge=1)
    budget: int = Field(default=8, ge=3)


class SequenceStrategy(LLMStrategy[SequenceParams]):
    name = "sequence"
    description = (
        "Sequence-based: opening questions and a first differential, then questions that "
        "prune it, then a confirming question for the leader."
    )
    params_model = SequenceParams

    def prompts(self) -> dict[str, str]:
        return {"ask": ASK, "draft": DRAFT, "prune": PRUNE, "settle": SETTLE, **dict(GOALS.items())}

    def new_session(self, context: CaseContext) -> SequenceSession:
        return SequenceSession(self, context)


class SequenceSession(LLMSession):
    strategy: SequenceStrategy

    def __init__(self, strategy: SequenceStrategy, context: CaseContext) -> None:
        super().__init__(strategy, context)
        params = strategy.params
        budget = max(3, context.max_iterations or params.budget)
        self.opening = max(1, round(params.opening_share * budget))
        self.final_from = budget - max(1, round(params.final_share * budget))  # questions asked
        self.phase: Phase = "init"
        self.candidates: list[str] = []
        self.pruned_at = 0  # the memory's length when the candidates were last rewritten
        self.final_asked = 0
        self.verdict: Verdict | None = None

    def render_candidates(self) -> str:
        return "Candidate diagnoses, most likely first: " + (
            "; ".join(self.candidates) or "(none yet)"
        )

    def rewrite(self, prompt: str, records: list[LLMCallRecord]) -> None:
        reply = self.call(
            prompt, f"{self.transcript()}\n\n{self.render_candidates()}", Candidates, records
        )
        self.candidates = [c.strip() for c in reply.candidates if c.strip()][:5]
        self.pruned_at = len(self.memory)

    def advance(self, records: list[LLMCallRecord]) -> bool:
        """Move through the phases as far as the answers allow; False once it is settled."""
        asked = len(self.memory)
        if self.phase == "init" and asked >= self.opening:
            self.rewrite(DRAFT, records)
            self.phase = "refine"
        if self.phase == "refine":
            if asked > self.pruned_at:
                self.rewrite(PRUNE, records)
            narrow = len(self.candidates) <= self.strategy.params.narrow_to
            if narrow or asked >= self.final_from:
                self.phase = "final"
        elif self.phase == "final" and self.final_asked:
            self.verdict = self.call(
                SETTLE, f"{self.transcript()}\n\n{self.render_candidates()}", Verdict, records
            )
            return not self.verdict.settled
        return True

    def next_question(self) -> Question | None:
        records: list[LLMCallRecord] = []
        if not self.advance(records):
            self.carried.extend(records)
            return None
        turn = self.call(
            ASK.format(goal=GOALS[self.phase]),
            f"{self.transcript()}\n\n{self.render_candidates()}\n\n{self.budget_line()} "
            "Ask the next question.",
            PhaseQuestion,
            records,
        )
        if not turn.question.strip():
            self.carried.extend(records)
            return None
        if self.phase == "final":
            self.final_asked += 1
        return Question(
            turn.question.strip(),
            turn.rationale.strip() or None,
            records,
            trace={"phase": self.phase, "candidates": list(self.candidates)},
        )

    def final_diagnosis(self) -> Diagnosis:
        notes = self.render_candidates()
        if self.verdict is not None:
            state = "settled" if self.verdict.settled else "still open"
            notes += f"\nDiagnosis held after the confirming question: {self.verdict.diagnosis} "
            notes += f"({state})."
        return self.diagnose(
            notes,
            trace={
                "phase": self.phase,
                "candidates": self.candidates,
                "verdict": self.verdict.model_dump() if self.verdict else None,
            },
        )
