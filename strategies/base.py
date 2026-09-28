"""The information gathering strategy interface.

A strategy object is built once per experiment and shared by the worker threads, so it holds only
configuration. Each case run gets its own session, which holds that run's memory: every question
asked so far and the answer the environment gave.

A strategy only ever sees ``EnvironmentResponse.output_answer``. The rest of the response
(literature queries, documents, retriever parameters) can reveal the diagnosis; see
environment/README.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from medsim.config import Settings
from medsim.llm.base import LLMClient
from medsim.models import LLMCallRecord


@dataclass(frozen=True)
class CaseContext:
    """What a strategy may know about a case before it asks anything."""

    max_iterations: int | None = None
    max_seconds: float | None = None


@dataclass(frozen=True)
class MemoryEntry:
    question: str
    answer: str


class Memory:
    """Every question and answer of one case run, in order."""

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []

    def add(self, question: str, answer: str) -> None:
        self._entries.append(MemoryEntry(question, answer))

    @property
    def entries(self) -> list[MemoryEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[MemoryEntry]:
        return iter(list(self._entries))

    def render(self) -> str:
        if not self._entries:
            return "(none yet)"
        return "\n".join(
            f"{i}. Q: {entry.question}\n   A: {entry.answer}"
            for i, entry in enumerate(self._entries, 1)
        )


@dataclass
class Question:
    text: str
    rationale: str | None = None
    llm_calls: list[LLMCallRecord] = field(default_factory=list)


class StrategyParams(BaseModel):
    """Base for a strategy's ``params`` in the experiment config; unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")


P = TypeVar("P", bound=StrategyParams)


class StrategySession(ABC):
    """One case run's view of a strategy: its memory and how it picks the next question."""

    def __init__(self, context: CaseContext) -> None:
        self.context = context
        self.memory = Memory()

    @abstractmethod
    def next_question(self) -> Question | None:
        """The next question to ask, or None when the strategy has nothing more to ask."""

    def remember(self, question: str, answer: str) -> None:
        self.memory.add(question, answer)


class InformationGatheringStrategy(ABC, Generic[P]):
    name: ClassVar[str]
    description: ClassVar[str]
    params_model: ClassVar[type[StrategyParams]] = StrategyParams  # the class P stands for

    def __init__(self, params: P, *, llm: LLMClient, settings: Settings) -> None:
        self.params = params
        self.llm = llm
        self.settings = settings  # the environment's settings (default model, seed)

    def models(self) -> list[str]:
        """OpenRouter model slugs this strategy calls; checked before an experiment starts."""
        return []

    @abstractmethod
    def new_session(self, context: CaseContext) -> StrategySession:
        """A fresh session with an empty memory, for one case run."""
