"""The "basic" strategy: an LLM reads everything collected so far and asks the next question.

One LLM call per question, with no planning or hypothesis tracking. It never stops by itself;
the experiment's stopping criteria end the case run.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from medsim.errors import LLMError, LLMTruncatedError
from medsim.llm.structured import call_structured
from medsim.models import ChatMessage, LLMCallRecord
from strategies.base import (
    CaseContext,
    InformationGatheringStrategy,
    Question,
    StrategyParams,
    StrategySession,
)

SYSTEM_PROMPT = """\
You are a clinician gathering information about a patient. You cannot see the patient's \
records. You can only ask questions, one at a time, and a simulated patient environment answers \
them. Your aim is to collect the information needed to reach a diagnosis.

Ask the single most useful next question:
- Ask about one thing: one symptom, history item, examination finding, measurement, or test \
result.
- Build on what you already know. Do not repeat a question that was already answered, and do \
not ask again for something the environment could not answer.
- Start broad (presenting complaint, history) and become more specific as the picture develops.
- Ask plainly about the patient in the third person (for example, "What is the patient's \
heart rate?"). Do not ask for the diagnosis; it is withheld.

Return only a JSON object with keys question (the question to ask) and rationale (one sentence \
on why it is the most useful next question)."""


class StrategyTurn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    rationale: str


class BasicParams(StrategyParams):
    model: str | None = None  # None = the environment's default model
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=1)  # includes reasoning tokens


class BasicStrategy(InformationGatheringStrategy[BasicParams]):
    name = "basic"
    description = (
        "An LLM reads the answers collected so far and asks the single most useful next "
        "question (one call per question)."
    )
    params_model = BasicParams

    @property
    def model(self) -> str:
        return self.params.model or self.settings.default_model

    def models(self) -> list[str]:
        return [self.model]

    def new_session(self, context: CaseContext) -> BasicSession:
        return BasicSession(self, context)


class BasicSession(StrategySession):
    def __init__(self, strategy: BasicStrategy, context: CaseContext) -> None:
        super().__init__(context)
        self.strategy = strategy

    def prompt(self) -> str:
        context = self.context
        number = len(self.memory) + 1
        budget = f" of at most {context.max_iterations}" if context.max_iterations else ""
        return (
            "You have no information about the patient yet.\n\n"
            f"Questions asked so far and the answers received:\n{self.memory.render()}\n\n"
            f"This is question {number}{budget}. Ask the next question."
        )

    def next_question(self) -> Question | None:
        params = self.strategy.params
        records: list[LLMCallRecord] = []
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=self.prompt()),
        ]
        try:
            turn = call_structured(
                self.strategy.llm,
                stage="strategy",
                messages=messages,
                output_model=StrategyTurn,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
                model=self.strategy.model,
                records=records,
            )
        except LLMTruncatedError as exc:
            raise LLMError(
                f"basic strategy: the reply was cut off at max_tokens={exc.max_tokens}, even "
                "after one retry with double the budget. Raise the strategy's max_tokens param."
            ) from None
        question = turn.question.strip()
        if not question:
            return None
        return Question(text=question, rationale=turn.rationale.strip() or None, llm_calls=records)
