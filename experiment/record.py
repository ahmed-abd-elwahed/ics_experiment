"""The experiment record: everything a run produced, saved as one JSON file.

While the experiment runs, each finished case run is appended to ``<record>.partial.jsonl`` (a
header line, then one line per case run), so finished work survives a crash. When the run ends
the complete record is written and the partial file is removed.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, Field

from experiment.config import ExperimentConfig, partial_path
from medsim.models import AnswerSource, CaseStudy, EnvironmentResponse, LLMCallRecord

logger = logging.getLogger("experiment.record")

RECORD_FORMAT: Final = "ics-experiment-record"
RECORD_VERSION = 1

StopReason = Literal["max_iterations", "max_seconds", "strategy_done", "cancelled", "error"]
CaseRunStatus = Literal["completed", "error", "cancelled"]
RecordStatus = Literal["running", "completed", "cancelled", "failed"]


class Iteration(BaseModel):
    """One question from the strategy and the environment's answer."""

    index: int  # 1-based
    started_at: str
    question: str
    rationale: str | None = None
    answer: str | None = None  # output_answer: the only part of the response the strategy sees
    answer_source: AnswerSource | None = None
    strategy_seconds: float
    environment_seconds: float | None = None
    strategy_llm_calls: list[LLMCallRecord] = Field(default_factory=list)
    # The full response, for evaluators. Retrieved documents are kept without their raw source
    # records to keep the file small.
    environment_response: EnvironmentResponse | None = None
    strategy_cost_usd: float = 0.0
    environment_cost_usd: float = 0.0
    error: str | None = None


class CaseRun(BaseModel):
    index: int  # position in the experiment: case order, then strategy order
    case_id: str
    strategy: str  # the strategy's label in the config
    strategy_name: str
    case: CaseStudy  # what was loaded into the environment (the diagnosis is never shown)
    status: CaseRunStatus
    stop_reason: StopReason
    error: str | None = None
    started_at: str
    finished_at: str
    elapsed_s: float
    iterations: list[Iteration] = Field(default_factory=list)
    strategy_cost_usd: float = 0.0
    environment_cost_usd: float = 0.0

    @property
    def cost_usd(self) -> float:
        return self.strategy_cost_usd + self.environment_cost_usd


class ExperimentRecord(BaseModel):
    format: Literal["ics-experiment-record"] = RECORD_FORMAT
    version: int = RECORD_VERSION
    name: str
    status: RecordStatus
    error: str | None = None
    started_at: str
    finished_at: str | None = None
    elapsed_s: float | None = None
    output: str
    config: ExperimentConfig
    environment_settings: dict[str, Any]  # resolved medsim settings, without the API key
    strategies: dict[str, dict[str, Any]]  # label -> name, description, resolved params
    code_version: dict[str, Any] = Field(default_factory=dict)
    case_ids: list[str]
    case_runs_total: int
    case_runs: list[CaseRun] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


# --- costs and compaction ---------------------------------------------------------------------


def calls_cost(calls: list[LLMCallRecord]) -> float:
    return sum(call.cost_usd or 0.0 for call in calls)


def environment_cost(response: EnvironmentResponse) -> float:
    """LLM calls plus billed searches (OpenRouter web search records a cost per attempt)."""
    total = calls_cost(response.llm_calls)
    params = response.retriever_parameters
    entries = (params.get("sub_queries") or []) if params.get("multi_part") else [params]
    for entry in entries:
        for info in (entry.get("per_source") or {}).values():
            for attempt in info.get("query_attempts") or []:
                total += float(attempt.get("cost_usd") or 0.0)
    return total


def compact_response(response: EnvironmentResponse) -> EnvironmentResponse:
    """The response without each retrieved document's raw source record."""
    result = response.literature_search_result
    if result is None:
        return response
    documents = [doc.model_copy(update={"raw": {}}) for doc in result.documents]
    return response.model_copy(
        update={"literature_search_result": result.model_copy(update={"documents": documents})}
    )


# --- summary ----------------------------------------------------------------------------------


def _group_summary(runs: list[CaseRun]) -> dict[str, Any]:
    iterations = [it for run in runs for it in run.iterations]
    answered = [it for it in iterations if it.answer_source is not None]
    env_seconds = [it.environment_seconds for it in iterations if it.environment_seconds]
    strategy_cost = sum(run.strategy_cost_usd for run in runs)
    environment_cost = sum(run.environment_cost_usd for run in runs)
    return {
        "case_runs": len(runs),
        "errors": sum(run.status == "error" for run in runs),
        "iterations": len(iterations),
        "mean_iterations": round(len(iterations) / len(runs), 2) if runs else 0.0,
        "stop_reasons": dict(Counter(run.stop_reason for run in runs)),
        "answer_sources": dict(Counter(it.answer_source for it in answered)),
        "mean_environment_seconds": (
            round(sum(env_seconds) / len(env_seconds), 2) if env_seconds else None
        ),
        "mean_case_run_seconds": (
            round(sum(run.elapsed_s for run in runs) / len(runs), 2) if runs else None
        ),
        "cost_usd": {
            "strategy": round(strategy_cost, 6),
            "environment": round(environment_cost, 6),
            "total": round(strategy_cost + environment_cost, 6),
        },
    }


def summarize(case_runs: list[CaseRun], strategy_keys: list[str]) -> dict[str, Any]:
    return {
        "overall": _group_summary(case_runs),
        "by_strategy": {
            key: _group_summary([run for run in case_runs if run.strategy == key])
            for key in strategy_keys
        },
    }


# --- files ------------------------------------------------------------------------------------


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class RecordWriter:
    """Saves each finished case run as it arrives, then the complete record (thread-safe)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.partial = partial_path(path)
        self._lock = threading.Lock()

    def start(self, record: ExperimentRecord) -> None:
        header = {"type": "header", **record.model_dump(mode="json", exclude={"case_runs"})}
        with self._lock:
            _write_atomic(self.partial, json.dumps(header, ensure_ascii=False) + "\n")

    def append(self, case_run: CaseRun) -> None:
        data = {"type": "case_run", **case_run.model_dump(mode="json")}
        line = json.dumps(data, ensure_ascii=False)
        with self._lock, self.partial.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def finish(self, record: ExperimentRecord) -> None:
        with self._lock:
            _write_atomic(self.path, record.model_dump_json(indent=2))
            self.partial.unlink(missing_ok=True)


def load_record(path: str | Path) -> ExperimentRecord:
    """A complete record (``.json``) or the partial file of an unfinished run (``.jsonl``)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".jsonl":
        return ExperimentRecord.model_validate_json(text)
    header: dict[str, Any] | None = None
    case_runs: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:  # a line cut short when the process stopped
            logger.warning("%s:%d is not valid JSON; skipped", path, number)
            continue
        kind = data.pop("type", None)
        if kind == "header":
            header = data
        elif kind == "case_run":
            case_runs.append(data)
    if header is None:
        raise ValueError(f"{path} has no header line; it is not an experiment record.")
    case_runs.sort(key=lambda run: int(run.get("index", 0)))
    return ExperimentRecord.model_validate({**header, "case_runs": case_runs})
