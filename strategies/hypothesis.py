"""Hypothesis-driven search (Meeting 63, slide 8).

Collect new information, update the hypothesis, and stop once it is satisficing: the leading
diagnosis is probable enough and clearly ahead of the runner-up.
"""

from __future__ import annotations

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

UPDATE = f"""\
{CLINICIAN}

Update your differential diagnosis with everything known so far. Give at most 5 hypotheses, \
each with its probability (the probabilities sum to 1) and the findings for and against it.

Return only a JSON object with the key hypotheses: a list of objects with keys diagnosis, \
probability, evidence_for and evidence_against."""

ASK = f"""\
{CLINICIAN}

You reason from hypotheses. Ask the question whose answer would most change the ranking of \
your differential: the one that best separates the leading hypotheses. With no differential \
yet, ask for the presenting complaint.

{QUESTION_RULES}

Return only a JSON object with keys question, separates (the hypotheses the answer would tell \
apart) and rationale (one sentence)."""


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    diagnosis: str
    probability: float
    evidence_for: str = ""
    evidence_against: str = ""


class Differential(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hypotheses: list[Hypothesis]


class SplittingQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    separates: list[str] = Field(default_factory=list)
    rationale: str = ""


class HypothesisParams(LLMStrategyParams):
    accept: float = Field(default=0.8, ge=0.0, le=1.0)  # the leader's probability
    margin: float = Field(default=0.3, ge=0.0, le=1.0)  # its lead over the runner-up


class HypothesisStrategy(LLMStrategy[HypothesisParams]):
    name = "hypothesis"
    description = (
        "Hypothesis-driven search: keeps a ranked differential, asks the question that best "
        "separates the leading hypotheses, and stops once one clearly leads."
    )
    params_model = HypothesisParams

    def prompts(self) -> dict[str, str]:
        return {"update": UPDATE, "ask": ASK}

    def new_session(self, context: CaseContext) -> HypothesisSession:
        return HypothesisSession(self, context)


class HypothesisSession(LLMSession):
    strategy: HypothesisStrategy

    def __init__(self, strategy: HypothesisStrategy, context: CaseContext) -> None:
        super().__init__(strategy, context)
        self.differential: list[Hypothesis] = []

    def render_differential(self) -> str:
        if not self.differential:
            return "Current differential: (none yet)"
        lines = [
            f"- {h.diagnosis} (p={h.probability:.2f}); for: {h.evidence_for or '-'}; "
            f"against: {h.evidence_against or '-'}"
            for h in self.differential
        ]
        return "Current differential:\n" + "\n".join(lines)

    def update(self, records: list[LLMCallRecord]) -> None:
        reply = self.call(
            UPDATE, f"{self.transcript()}\n\n{self.render_differential()}", Differential, records
        )
        hypotheses = [h for h in reply.hypotheses if h.diagnosis.strip() and h.probability > 0]
        total = sum(h.probability for h in hypotheses)
        self.differential = sorted(
            (h.model_copy(update={"probability": h.probability / total}) for h in hypotheses),
            key=lambda h: -h.probability,
        )[:5]

    def satisficing(self) -> bool:
        if not self.differential:
            return False
        params = self.strategy.params
        top = self.differential[0].probability
        second = self.differential[1].probability if len(self.differential) > 1 else 0.0
        return top >= params.accept and top - second >= params.margin

    def next_question(self) -> Question | None:
        records: list[LLMCallRecord] = []
        if len(self.memory):  # nothing to update before the first answer
            self.update(records)
            if self.satisficing():
                self.carried.extend(records)
                return None
        turn = self.call(
            ASK,
            f"{self.transcript()}\n\n{self.render_differential()}\n\n{self.budget_line()} "
            "Ask the next question.",
            SplittingQuestion,
            records,
        )
        if not turn.question.strip():
            self.carried.extend(records)
            return None
        return Question(
            turn.question.strip(),
            turn.rationale.strip() or None,
            records,
            trace={"differential": self.dump(), "separates": turn.separates},
        )

    def dump(self) -> list[dict[str, object]]:
        return [h.model_dump() for h in self.differential]

    def final_diagnosis(self) -> Diagnosis:
        return self.diagnose(
            self.render_differential().replace("Current", "Differential before the last answer"),
            trace={"differential": self.dump(), "satisficing": self.satisficing()},
            style="Update the differential with the last answer and extend it to 10 entries.",
        )
