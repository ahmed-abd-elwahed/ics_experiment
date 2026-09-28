"""Test doubles for experiments: a scripted strategy, a canned environment, a manual clock."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from experiment.config import ExperimentConfig, parse_config
from medsim.errors import LLMError
from medsim.models import CaseStudy, EnvironmentResponse, LLMCallRecord
from strategies.base import (
    CaseContext,
    InformationGatheringStrategy,
    Question,
    StrategyParams,
    StrategySession,
)
from tests.conftest import ScriptedLLM, make_settings

CASES = [
    {
        "case_id": f"CASE{i}",
        "diagnosis": f"Diagnosis {i}",
        "case_information": f"Patient {i} presented with fever. Case {i}, second part.",
    }
    for i in range(1, 7)
]


def write_cases(directory: Path, cases: list[dict[str, Any]] | None = None) -> Path:
    path = directory / "cases.json"
    path.write_text(json.dumps(CASES if cases is None else cases), encoding="utf-8")
    return path


def make_config(cases_file: Path, **overrides: Any) -> ExperimentConfig:
    data: dict[str, Any] = {
        "name": "test",
        "cases_file": str(cases_file),
        "strategies": ["scripted"],
        "stopping": {"max_iterations": 3},
        "workers": 1,
        "output": str(cases_file.parent / "records" / "{name}.json"),
    }
    data.update(overrides)
    return parse_config(data)


def response(question: str, answer: str, *, cost: float = 0.001) -> EnvironmentResponse:
    return EnvironmentResponse(
        input_query=question,
        output_answer=answer,
        literature_search=False,
        literature_search_result=None,
        retriever_parameters={"multi_part": False, "path": "case_study"},
        used_llm="test/model",
        answer_source="case_study",
        evidence=[],
        confidence="high",
        llm_calls=[
            LLMCallRecord(
                stage="resolver", model="test/model", prompt_tokens=10, completion_tokens=5,
                latency_ms=1.0, cost_usd=cost,
            )
        ],
    )  # fmt: skip


class ManualClock:
    """A clock that only moves when told to (thread-safe)."""

    def __init__(self) -> None:
        self.now = 0.0
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            return self.now

    def advance(self, seconds: float) -> None:
        with self._lock:
            self.now += seconds


class FakeEnvironment:
    """Answers "answer <n> for <case id>"; can fail on a given query or advance a clock."""

    def __init__(
        self,
        case: CaseStudy,
        *,
        fail_on: int | None = None,
        clock: ManualClock | None = None,
        seconds_per_query: float = 0.0,
        sleep: float = 0.0,
        tracker: ConcurrencyTracker | None = None,
    ) -> None:
        self.case = case
        self.queries: list[str] = []
        self._fail_on = fail_on
        self._clock = clock
        self._seconds = seconds_per_query
        self._sleep = sleep
        self._tracker = tracker

    def query(self, query: str) -> EnvironmentResponse:
        self.queries.append(query)
        if self._tracker:
            self._tracker.enter()
        try:
            if self._sleep:
                time.sleep(self._sleep)
        finally:
            if self._tracker:
                self._tracker.leave()
        if self._clock is not None:
            self._clock.advance(self._seconds)
        if self._fail_on is not None and len(self.queries) == self._fail_on:
            raise LLMError("resolver: OpenRouter HTTP 502")
        return response(query, f"answer {len(self.queries)} for {self.case.case_id}")


class ConcurrencyTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.current = 0
        self.peak = 0

    def enter(self) -> None:
        with self._lock:
            self.current += 1
            self.peak = max(self.peak, self.current)

    def leave(self) -> None:
        with self._lock:
            self.current -= 1


class ScriptedSession(StrategySession):
    def __init__(self, strategy: ScriptedStrategy, context: CaseContext) -> None:
        super().__init__(context)
        self.strategy = strategy
        self.seen: list[list[tuple[str, str]]] = []  # the memory at each question

    def next_question(self) -> Question | None:
        self.seen.append([(e.question, e.answer) for e in self.memory])
        number = len(self.memory) + 1
        if self.strategy.stop_after is not None and number > self.strategy.stop_after:
            return None
        calls = [
            LLMCallRecord(
                stage="strategy", model="test/strategy", prompt_tokens=20, completion_tokens=5,
                latency_ms=1.0, cost_usd=0.0005,
            )
        ]  # fmt: skip
        return Question(text=f"{self.strategy.prefix} question {number}?", rationale="because",
                        llm_calls=calls)  # fmt: skip


class ScriptedStrategy(InformationGatheringStrategy[StrategyParams]):
    name = "scripted"
    description = "Asks numbered questions."

    def __init__(self, *, prefix: str = "Q", stop_after: int | None = None) -> None:
        super().__init__(StrategyParams(), llm=ScriptedLLM(), settings=make_settings())
        self.prefix = prefix
        self.stop_after = stop_after
        self.sessions: list[ScriptedSession] = []
        self._lock = threading.Lock()

    def new_session(self, context: CaseContext) -> ScriptedSession:
        session = ScriptedSession(self, context)
        with self._lock:
            self.sessions.append(session)
        return session
