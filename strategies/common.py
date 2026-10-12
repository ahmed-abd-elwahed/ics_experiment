"""What the five strategies of Meeting 63 (slides 8 to 12) share: params, the LLM call helper,
and the final differential.

In each strategy the LLM estimates (a probability, a label, a list) and code decides when to
stop, by comparing those values with thresholds in the strategy's params.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from medsim.errors import LLMError, LLMTruncatedError
from medsim.llm.structured import call_structured
from medsim.models import ChatMessage, LLMCallRecord
from strategies.base import (
    CaseContext,
    Diagnosis,
    InformationGatheringStrategy,
    RankedDiagnosis,
    StrategyParams,
    StrategySession,
)

T = TypeVar("T", bound=BaseModel)

CLINICIAN = """\
You are a clinician working up a patient. You cannot see the patient's records. You can only \
ask questions, one at a time, and a simulated patient environment answers them."""

QUESTION_RULES = """\
Rules for the question:
- Ask about one thing: one symptom, history item, examination finding, measurement, or test \
result.
- Do not repeat a question that was already answered, and do not ask again for something the \
environment could not answer.
- Ask plainly about the patient in the third person (for example, "What is the patient's \
heart rate?"). Do not ask for the diagnosis; it is withheld."""

DIAGNOSE = """\
You are a clinician. From the questions asked about a patient and the answers received, give \
the differential diagnosis.

Return only a JSON object with the key differential: a list of exactly 10 objects with keys \
diagnosis and probability, ordered from the most to the least likely.
- diagnosis: one specific disease or condition, named as it would appear in ICD-11, without \
abbreviations, qualifiers in brackets, or explanations.
- probability: a number between 0 and 1. No two entries may have the same probability."""

DIFFERENTIAL_SIZE = 10


class RankedEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    diagnosis: str
    probability: float


class FinalDifferential(BaseModel):
    model_config = ConfigDict(extra="ignore")

    differential: list[RankedEntry]


class LLMStrategyParams(StrategyParams):
    model: str | None = None  # None = the environment's default model
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1)  # includes reasoning tokens


P = TypeVar("P", bound=LLMStrategyParams)


class LLMStrategy(InformationGatheringStrategy[P], Generic[P]):
    """A strategy whose every step is a call to one model."""

    @property
    def model(self) -> str:
        return self.params.model or self.settings.default_model

    def models(self) -> list[str]:
        return [self.model]


class LLMSession(StrategySession):
    def __init__(self, strategy: LLMStrategy[Any], context: CaseContext) -> None:
        super().__init__(context)
        self.strategy = strategy
        # Calls made while deciding to stop: there is no question to attach them to, so they
        # are saved with the diagnosis.
        self.carried: list[LLMCallRecord] = []

    def transcript(self) -> str:
        return f"Questions asked so far and the answers received:\n{self.memory.render()}"

    def budget_line(self) -> str:
        number = len(self.memory) + 1
        limit = self.context.max_iterations
        return f"This is question {number}{f' of at most {limit}' if limit else ''}."

    def call(
        self,
        system: str,
        user: str,
        output_model: type[T],
        records: list[LLMCallRecord],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> T:
        params = self.strategy.params
        budget = max_tokens or params.max_tokens
        try:
            return call_structured(
                self.strategy.llm,
                stage="strategy",
                messages=[
                    ChatMessage(role="system", content=system),
                    ChatMessage(role="user", content=user),
                ],
                output_model=output_model,
                temperature=params.temperature if temperature is None else temperature,
                max_tokens=budget,
                model=self.strategy.model,
                records=records,
            )
        except LLMTruncatedError as exc:
            raise LLMError(
                f"{self.strategy.name} strategy: the reply was cut off at "
                f"max_tokens={exc.max_tokens}, even after one retry with double the budget. "
                "Raise the strategy's max_tokens param."
            ) from None

    def call_many(
        self,
        system: str,
        user: str,
        output_model: type[T],
        records: list[LLMCallRecord],
        *,
        n: int,
        temperature: float,
        max_tokens: int | None = None,
    ) -> list[T]:
        """The same call ``n`` times at once; the samples differ through the temperature."""

        def one(_: int) -> tuple[T, list[LLMCallRecord]]:
            own: list[LLMCallRecord] = []
            result = self.call(
                system, user, output_model, own, temperature=temperature, max_tokens=max_tokens
            )
            return result, own

        with ThreadPoolExecutor(max_workers=n, thread_name_prefix="strategy-vote") as pool:
            results = list(pool.map(one, range(n)))
        for _, own in results:
            records.extend(own)
        return [result for result, _ in results]

    def diagnose(
        self, notes: str = "", *, trace: dict[str, Any] | None = None, style: str = ""
    ) -> Diagnosis:
        """The final differential: one call that reads the memory and the strategy's notes."""
        records = list(self.carried)
        parts = [self.transcript()]
        if notes:
            parts.append(notes)
        parts.append(style or "Give the differential diagnosis.")
        reply = self.call(DIAGNOSE, "\n\n".join(parts), FinalDifferential, records)
        return Diagnosis(ranked(reply.differential), llm_calls=records, trace=trace or {})


def ranked(entries: list[RankedEntry]) -> list[RankedDiagnosis]:
    """Named entries, most likely first; the model's own order breaks ties."""
    seen: set[str] = set()
    kept: list[RankedDiagnosis] = []
    for entry in entries:
        name = " ".join(entry.diagnosis.split())
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        kept.append(RankedDiagnosis(name, min(1.0, max(0.0, entry.probability))))
    kept.sort(key=lambda d: -d.probability)  # stable
    return kept[:DIFFERENTIAL_SIZE]
