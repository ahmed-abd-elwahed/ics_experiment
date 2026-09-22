"""Live progress of a running experiment, for the CLI's progress line and the web app."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from experiment.record import CaseRun, ExperimentRecord, Iteration
from experiment.runner import Clock, ExperimentListener


class ProgressTracker(ExperimentListener):
    """Thread-safe counters and the case runs in flight; ``snapshot()`` is JSON-ready."""

    def __init__(self, *, clock: Clock = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self.state = "preparing"  # then running, completed, cancelled, or failed
        self.error: str | None = None
        self.name = ""
        self.output: str | None = None
        self.total = 0
        self.finished = 0
        self.errors = 0
        self.iterations = 0
        self.cost_usd = 0.0
        self.max_iterations: int | None = None
        self.max_seconds: float | None = None
        self._started: float | None = None
        self._ended: float | None = None
        self._active: dict[int, dict[str, Any]] = {}
        self._recent: deque[dict[str, Any]] = deque(maxlen=100)

    # -- listener events ------------------------------------------------------------------------

    def experiment_started(self, record: ExperimentRecord) -> None:
        with self._lock:
            self.state = "running"
            self.name = record.name
            self.output = record.output
            self.total = record.case_runs_total
            self.max_iterations = record.config.stopping.max_iterations
            self.max_seconds = record.config.stopping.max_seconds
            self._started = self._clock()

    def case_started(self, index: int, case_id: str, strategy: str) -> None:
        with self._lock:
            self._active[index] = {
                "index": index, "case_id": case_id, "strategy": strategy, "iterations": 0,
                "started": self._clock(),
            }  # fmt: skip

    def iteration_finished(self, index: int, iteration: Iteration) -> None:
        with self._lock:
            if index in self._active:
                self._active[index]["iterations"] += 1
            self.iterations += 1
            self.cost_usd += iteration.strategy_cost_usd + iteration.environment_cost_usd

    def case_finished(self, case_run: CaseRun) -> None:
        with self._lock:
            self._active.pop(case_run.index, None)
            self.finished += 1
            self.errors += case_run.status == "error"
            self._recent.appendleft(
                {
                    "index": case_run.index,
                    "case_id": case_run.case_id,
                    "strategy": case_run.strategy,
                    "status": case_run.status,
                    "stop_reason": case_run.stop_reason,
                    "iterations": len(case_run.iterations),
                    "elapsed_s": case_run.elapsed_s,
                    "cost_usd": round(case_run.cost_usd, 6),
                    "error": case_run.error,
                }
            )

    def experiment_finished(self, record: ExperimentRecord) -> None:
        with self._lock:
            self.state = record.status
            self.error = record.error
            self._ended = self._clock()

    def fail(self, error: str) -> None:
        """The experiment could not start or stopped with an error."""
        with self._lock:
            self.state = "failed"
            self.error = error
            self._ended = self._clock()

    # -- reading --------------------------------------------------------------------------------

    def _run_fraction(self, run: dict[str, Any], now: float) -> float:
        parts = []
        if self.max_iterations:
            parts.append(run["iterations"] / self.max_iterations)
        if self.max_seconds:
            parts.append((now - run["started"]) / self.max_seconds)
        return min(max(parts, default=0.0), 0.99)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = self._clock()
            elapsed = 0.0
            if self._started is not None:
                elapsed = (self._ended if self._ended is not None else now) - self._started
            partial = sum(self._run_fraction(run, now) for run in self._active.values())
            if self.state == "completed":
                fraction = 1.0
            else:
                fraction = min((self.finished + partial) / self.total, 1.0) if self.total else 0.0
            eta = None
            if self.state == "running" and fraction >= 0.01:
                eta = elapsed * (1 - fraction) / fraction
            active = [
                {
                    **{k: v for k, v in run.items() if k != "started"},
                    "elapsed_s": round(now - run["started"], 1),
                    "fraction": round(self._run_fraction(run, now), 3),
                }
                for run in sorted(self._active.values(), key=lambda r: r["index"])
            ]
            return {
                "state": self.state,
                "error": self.error,
                "name": self.name,
                "output": self.output,
                "total": self.total,
                "finished": self.finished,
                "errors": self.errors,
                "iterations": self.iterations,
                "cost_usd": round(self.cost_usd, 6),
                "fraction": round(fraction, 4),
                "elapsed_s": round(elapsed, 1),
                "eta_s": round(eta, 1) if eta is not None else None,
                "max_iterations": self.max_iterations,
                "max_seconds": self.max_seconds,
                "active": active,
                "recent": list(self._recent),
            }
