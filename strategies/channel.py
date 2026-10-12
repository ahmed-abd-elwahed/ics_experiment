"""Channel-based collection (Meeting 63, slide 11).

Conduct the patient interview; if that does not give a confident diagnosis, go on to the
physical exam. A channel is a kind of source, and questions are confined to the current one.
"""

from __future__ import annotations

from typing import Any, Literal

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

Channel = Literal["interview", "exam"]
QuestionKind = Literal["interview", "exam", "test"]


def _default_channels() -> list[Channel]:
    return ["interview", "exam"]


CHANNELS: dict[Channel, str] = {
    "interview": (
        "the patient interview: only what the patient or family can tell you, such as "
        "symptoms, their onset and course, past illnesses, medication, family and social "
        "history. No examination findings, measurements or tests."
    ),
    "exam": (
        "the physical examination: only what a clinician finds at the bedside, such as vital "
        "signs, inspection, palpation, percussion, auscultation and the neurological "
        "examination. No history, laboratory tests or imaging."
    ),
}

ASK = f"""\
{CLINICIAN}

You are collecting information through one channel at a time. The current channel is \
{{channel}}

Ask the most useful next question within this channel. If nothing useful is left to ask in \
this channel, set nothing_left to true and leave the question empty.

{QUESTION_RULES}

Return only a JSON object with keys question, nothing_left and rationale (one sentence)."""

CLASSIFY = """\
Label a clinician's question about a patient by where its answer comes from:
- interview: what the patient or family reports (symptoms, history, medication, exposures).
- exam: what a clinician finds at the bedside (vital signs, inspection, palpation, \
auscultation, neurological examination).
- test: laboratory tests, imaging, pathology, or any other investigation.

Return only a JSON object with the key kind."""

ASSESS = f"""\
{CLINICIAN}

Commit to the single most likely diagnosis from what is known so far, and say how confident \
you are that it is correct, from 0 (a guess) to 1 (certain).

Return only a JSON object with keys diagnosis and confidence."""


class ChannelQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str = ""
    nothing_left: bool = False
    rationale: str = ""


class Kind(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: QuestionKind


class Assessment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    diagnosis: str
    confidence: float


class ChannelParams(LLMStrategyParams):
    channels: list[Channel] = Field(default_factory=_default_channels, min_length=1)
    # Questions per channel; None = the iteration limit divided evenly over the channels.
    questions_per_channel: int | None = Field(default=None, ge=1)
    confident: float = Field(default=0.8, ge=0.0, le=1.0)
    reasks: int = Field(default=2, ge=0)  # new attempts after a question outside the channel


class ChannelStrategy(LLMStrategy[ChannelParams]):
    name = "channel"
    description = (
        "Channel-based: the patient interview first; if that leaves the diagnosis uncertain, "
        "the physical exam. Questions outside the current channel are rejected."
    )
    params_model = ChannelParams

    def prompts(self) -> dict[str, str]:
        return {"ask": ASK, "classify": CLASSIFY, "assess": ASSESS, **dict(CHANNELS.items())}

    def new_session(self, context: CaseContext) -> ChannelSession:
        return ChannelSession(self, context)


class ChannelSession(LLMSession):
    strategy: ChannelStrategy

    def __init__(self, strategy: ChannelStrategy, context: CaseContext) -> None:
        super().__init__(strategy, context)
        params = strategy.params
        self.position = 0  # index of the current channel
        self.asked = 0  # questions asked in the current channel
        self.exhausted = False  # the LLM had nothing left to ask in the current channel
        self.cap = params.questions_per_channel or max(
            1, (context.max_iterations or 2 * len(params.channels)) // len(params.channels)
        )
        self.assessments: list[dict[str, Any]] = []
        self.rejected: list[dict[str, str]] = []

    @property
    def channel(self) -> Channel:
        return self.strategy.params.channels[self.position]

    def ask(self, records: list[LLMCallRecord]) -> ChannelQuestion | None:
        """A question inside the current channel, or None when the channel has no more."""
        feedback = ""
        for _ in range(self.strategy.params.reasks + 1):
            turn = self.call(
                ASK.format(channel=CHANNELS[self.channel]),
                f"{self.transcript()}\n\n{self.budget_line()} Ask the next question.{feedback}",
                ChannelQuestion,
                records,
            )
            question = turn.question.strip()
            if turn.nothing_left or not question:
                return None
            kind = self.call(CLASSIFY, f"Question: {question}", Kind, records, max_tokens=300).kind
            if kind == self.channel:
                return turn
            self.rejected.append({"channel": self.channel, "question": question, "kind": kind})
            feedback = (
                f'\n\nYour question "{question}" was rejected: it belongs to the {kind} '
                "channel. Ask one inside the current channel."
            )
        return None

    def next_question(self) -> Question | None:
        params = self.strategy.params
        records: list[LLMCallRecord] = []
        while True:
            turn = None
            if self.asked < self.cap and not self.exhausted:
                turn = self.ask(records)
            if turn is not None:
                self.asked += 1
                return Question(
                    turn.question.strip(),
                    turn.rationale.strip() or None,
                    records,
                    trace={
                        "channel": self.channel,
                        "assessments": list(self.assessments),
                        "rejected": list(self.rejected),
                    },
                )
            # The channel is used up. The slide asks "confident in diagnosis?" here; after the
            # last channel there is nothing more to open, so the diagnosis follows either way.
            if self.position == len(params.channels) - 1:
                self.carried.extend(records)
                return None
            view = self.call(ASSESS, self.transcript(), Assessment, records)
            self.assessments.append({"after": self.channel, **view.model_dump()})
            if view.confidence >= params.confident:
                self.carried.extend(records)
                return None
            self.position, self.asked, self.exhausted = self.position + 1, 0, False

    def final_diagnosis(self) -> Diagnosis:
        notes = ""
        if self.assessments:
            last = self.assessments[-1]
            notes = (
                f"Working diagnosis after the {last['after']}: {last['diagnosis']} "
                f"(confidence {last['confidence']:.2f})."
            )
        return self.diagnose(
            notes,
            trace={
                "channel": self.channel,
                "assessments": self.assessments,
                "rejected": self.rejected,
            },
        )
