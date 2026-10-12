"""Gut feeling (Meeting 63, slide 10).

Collect new information and read the current sense: alarm means keep asking, reassurance means
return the diagnosis. Every call is short and asks for no reasoning, and nothing is kept
between questions but the memory.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from medsim.models import LLMCallRecord
from strategies.base import CaseContext, Diagnosis, Question
from strategies.common import (
    CLINICIAN,
    QUESTION_RULES,
    LLMSession,
    LLMStrategy,
    LLMStrategyParams,
)

SENSE = f"""\
{CLINICIAN}

Go with your gut. Do not reason it through. What is your sense about this patient right now?
- alarm: something does not fit, or something is missing; you would not settle on a diagnosis.
- reassurance: the picture fits; you feel sure what this is.

Return only a JSON object with the key sense, either "alarm" or "reassurance"."""

ASK_FAST = f"""\
{CLINICIAN}

Go with your gut. Do not reason it through. Ask the first thing you want to know next. With \
nothing known yet, ask for the presenting complaint.

{QUESTION_RULES}

Return only a JSON object with the key question."""

IMPRESSION = "Go with your first impression. Do not deliberate."


class Sense(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sense: Literal["alarm", "reassurance"]


class BareQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str


class GutParams(LLMStrategyParams):
    votes: int = Field(default=5, ge=1, le=15)  # the sense is read this many times at once
    needed: int = Field(default=4, ge=1)  # votes for reassurance that stop the run
    # One word carries no confidence, so the readings must differ for their agreement to mean
    # anything; a model that honours the environment's seed would return the same word each time.
    vote_temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    # A reading is about 13 tokens, but in the pilot one reply ran past 100.
    vote_max_tokens: int = Field(default=300, ge=1)
    question_max_tokens: int = Field(default=300, ge=1)

    @model_validator(mode="after")
    def _needed_within_votes(self) -> GutParams:
        if self.needed > self.votes:
            raise ValueError("needed cannot be more than votes")
        return self


class GutStrategy(LLMStrategy[GutParams]):
    name = "gut"
    description = (
        "Gut feeling: unreasoned calls throughout; several one-word readings of the current "
        "sense decide between alarm (keep asking) and reassurance (stop)."
    )
    params_model = GutParams

    def prompts(self) -> dict[str, str]:
        return {"sense": SENSE, "ask": ASK_FAST, "impression": IMPRESSION}

    def new_session(self, context: CaseContext) -> GutSession:
        return GutSession(self, context)


class GutSession(LLMSession):
    strategy: GutStrategy

    def __init__(self, strategy: GutStrategy, context: CaseContext) -> None:
        super().__init__(strategy, context)
        self.senses: list[list[str]] = []  # the votes after each answer

    def next_question(self) -> Question | None:
        params = self.strategy.params
        records: list[LLMCallRecord] = []
        if len(self.memory):
            votes = self.call_many(
                SENSE, self.transcript(), Sense, records,
                n=params.votes, temperature=params.vote_temperature,
                max_tokens=params.vote_max_tokens,
            )  # fmt: skip
            self.senses.append([v.sense for v in votes])
            if self.senses[-1].count("reassurance") >= params.needed:
                self.carried.extend(records)
                return None
        turn = self.call(
            ASK_FAST, f"{self.transcript()}\n\nAsk the next question.", BareQuestion, records,
            max_tokens=params.question_max_tokens,
        )  # fmt: skip
        if not turn.question.strip():
            self.carried.extend(records)
            return None
        return Question(turn.question.strip(), None, records, trace={"senses": self.senses[-1:]})

    def final_diagnosis(self) -> Diagnosis:
        return self.diagnose(trace={"senses": self.senses}, style=IMPRESSION)
