"""Runs an experiment: every selected case with every strategy in the config.

Each (case, strategy) pair is a case run. The case is loaded into a fresh environment, and the
strategy asks questions until a stopping criterion is reached; every answer goes into the
strategy's memory for that case run. Case runs are independent, so they run in parallel threads
(``workers`` in the config). The iterations inside a case run are sequential, because each
question depends on the answers before it.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiment.config import (
    ExperimentConfig,
    environment_settings,
    initial_information,
    output_path,
    public_settings,
    select_cases,
)
from experiment.environment import Environment, EnvironmentFactory, MedsimEnvironmentFactory
from experiment.record import (
    CaseRun,
    CaseRunStatus,
    ExperimentRecord,
    Iteration,
    RecordStatus,
    RecordWriter,
    StopReason,
    calls_cost,
    compact_response,
    environment_cost,
    summarize,
)
from medsim.config import Settings
from medsim.errors import ConfigError, MedSimError
from medsim.llm.base import LLMClient
from medsim.llm.openrouter import OpenRouterClient
from medsim.models import CaseStudy
from strategies import InformationGatheringStrategy, build_strategy
from strategies.base import CaseContext, StrategySession

logger = logging.getLogger("experiment.runner")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
Clock = Callable[[], float]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def code_version() -> dict[str, Any]:
    """The git commit the experiment ran on, when the project is a git checkout."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10,
            check=True,
        ).stdout  # fmt: skip

    try:
        return {
            "git_commit": git("rev-parse", "HEAD").strip(),
            "uncommitted_changes": bool(git("status", "--porcelain").strip()),
        }
    except (OSError, subprocess.SubprocessError):
        return {}


class ExperimentListener:
    """Progress events; override the ones you need. Methods are called from worker threads."""

    def experiment_started(self, record: ExperimentRecord) -> None:
        pass

    def case_started(self, index: int, case_id: str, strategy: str) -> None:
        pass

    def iteration_finished(self, index: int, iteration: Iteration) -> None:
        pass

    def case_finished(self, case_run: CaseRun) -> None:
        pass

    def experiment_finished(self, record: ExperimentRecord) -> None:
        pass


@dataclass
class ExperimentPlan:
    """Everything a run needs, built by ``ExperimentRunner.prepare``."""

    cases: list[CaseStudy]
    settings: Settings
    llm: LLMClient
    strategies: dict[str, InformationGatheringStrategy[Any]]  # config label -> strategy
    environment_factory: EnvironmentFactory
    output: Path

    @property
    def case_runs(self) -> int:
        return len(self.cases) * len(self.strategies)


class ExperimentRunner:
    def __init__(
        self,
        config: ExperimentConfig,
        *,
        listener: ExperimentListener | None = None,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        environment_factory: EnvironmentFactory | None = None,
        strategies: Mapping[str, InformationGatheringStrategy[Any]] | None = None,
        verify_models: bool | None = None,  # None = the settings' verify_models_on_startup
        output: Path | None = None,
        clock: Clock = time.monotonic,
    ) -> None:
        self.config = config
        self.listener = listener or ExperimentListener()
        self._settings = settings
        self._llm = llm
        self._environment_factory = environment_factory
        self._strategies = dict(strategies) if strategies is not None else None
        self._verify_models = verify_models
        self._output = output
        self._clock = clock
        self._cancel = threading.Event()
        self._closers: list[Callable[[], None]] = []
        self._plan: ExperimentPlan | None = None

    # -- setup ----------------------------------------------------------------------------------

    def prepare(self) -> ExperimentPlan:
        """Load the cases and build the LLM client, strategies, and environment factory.

        Every configuration problem raises ``ConfigError`` here, before anything is spent.
        """
        if self._plan is not None:
            return self._plan
        try:
            self._plan = self._build_plan()
        except BaseException:
            self.close()
            raise
        return self._plan

    def _build_plan(self) -> ExperimentPlan:
        config = self.config
        cases = select_cases(config)
        settings = self._settings or environment_settings(config)
        llm = self._llm
        if llm is None:
            client = OpenRouterClient(settings)
            self._closers.append(client.close)
            llm = client
        if self._strategies is not None:
            missing = [key for key in config.strategy_keys if key not in self._strategies]
            if missing:
                raise ConfigError(f"No strategy object given for {', '.join(missing)}.")
            strategies = {key: self._strategies[key] for key in config.strategy_keys}
        else:
            strategies = {
                spec.key: build_strategy(spec.name, spec.params, llm=llm, settings=settings)
                for spec in config.strategies
            }
        verify = (
            settings.verify_models_on_startup if self._verify_models is None
            else self._verify_models
        )  # fmt: skip
        if verify and isinstance(llm, OpenRouterClient):
            models = [m for s in strategies.values() for m in s.models()]
            llm.verify_models([*settings.stage_models(), *models])
        factory = self._environment_factory
        if factory is None:
            medsim_factory = MedsimEnvironmentFactory(settings, llm)
            self._closers.append(medsim_factory.close)
            factory = medsim_factory
        output = self._output or output_path(config, now=datetime.now(UTC))
        return ExperimentPlan(cases, settings, llm, strategies, factory, output)

    def close(self) -> None:
        """Release the clients this runner created (not the ones passed in)."""
        while self._closers:
            closer = self._closers.pop()
            try:
                closer()
            except Exception:
                logger.exception("closing a client failed")

    def cancel(self) -> None:
        """Stop soon: running case runs stop before their next iteration, pending ones never
        start, and the record is saved with status "cancelled"."""
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    # -- the experiment -------------------------------------------------------------------------

    def run(self) -> ExperimentRecord:
        plan = self.prepare()
        config = self.config
        tasks = [(case, key) for case in plan.cases for key in plan.strategies]
        started = self._clock()
        record = ExperimentRecord(
            name=config.name,
            status="running",
            started_at=utc_now(),
            output=str(plan.output),
            config=config,
            environment_settings=public_settings(plan.settings),
            strategies={
                key: {
                    "name": strategy.name,
                    "description": strategy.description,
                    "params": strategy.params.model_dump(mode="json"),
                    "models": strategy.models(),
                }
                for key, strategy in plan.strategies.items()
            },
            code_version=code_version(),
            case_ids=[case.case_id for case in plan.cases],
            case_runs_total=len(tasks),
        )
        writer = RecordWriter(plan.output)
        writer.start(record)
        self._emit("experiment_started", record)
        results: dict[int, CaseRun] = {}
        futures: list[Future[CaseRun | None]] = []
        try:
            workers = min(config.workers, len(tasks))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="case-run") as pool:
                futures = [
                    pool.submit(self._run_case, index, case, key)
                    for index, (case, key) in enumerate(tasks)
                ]
                try:
                    for future in as_completed(futures):
                        self._collect(future.result(), results, writer)
                except BaseException:
                    self._cancel.set()  # running case runs stop before their next iteration
                    raise
        except BaseException as exc:
            # Ctrl+C or an unexpected fault: keep every case run that finished.
            for future in futures:
                if future.done() and not future.cancelled() and future.exception() is None:
                    self._collect(future.result(), results, writer)
            interrupted = isinstance(exc, KeyboardInterrupt)
            status: RecordStatus = "cancelled" if interrupted else "failed"
            error = None if interrupted else f"{type(exc).__name__}: {exc}"
            try:
                self._finish(record, results, writer, started, status, error)
            except Exception:
                logger.exception("could not save the experiment record")
            raise
        finally:
            self.close()
        status = "cancelled" if self._cancel.is_set() else "completed"
        return self._finish(record, results, writer, started, status, None)

    def _collect(
        self, case_run: CaseRun | None, results: dict[int, CaseRun], writer: RecordWriter
    ) -> None:
        if case_run is None or case_run.index in results:  # not started, or already saved
            return
        results[case_run.index] = case_run
        writer.append(case_run)
        self._emit("case_finished", case_run)

    def _finish(
        self,
        record: ExperimentRecord,
        results: dict[int, CaseRun],
        writer: RecordWriter,
        started: float,
        status: RecordStatus,
        error: str | None,
    ) -> ExperimentRecord:
        case_runs = [results[index] for index in sorted(results)]
        record = record.model_copy(
            update={
                "status": status,
                "error": error,
                "finished_at": utc_now(),
                "elapsed_s": round(self._clock() - started, 2),
                "case_runs": case_runs,
                "summary": summarize(case_runs, self.config.strategy_keys),
            }
        )
        writer.finish(record)
        self._emit("experiment_finished", record)
        return record

    # -- one case run ---------------------------------------------------------------------------

    def _run_case(self, index: int, case: CaseStudy, key: str) -> CaseRun | None:
        if self._cancel.is_set():
            return None  # cancelled before it started
        assert self._plan is not None
        plan = self._plan
        strategy = plan.strategies[key]
        stopping = self.config.stopping
        initial = initial_information(case, self.config.initial_information)
        self._emit("case_started", index, case.case_id, key)
        started_at, started = utc_now(), self._clock()
        iterations: list[Iteration] = []
        status: CaseRunStatus = "completed"
        stop_reason: StopReason
        error: str | None = None
        try:
            environment = plan.environment_factory(case)
            session = strategy.new_session(
                CaseContext(initial, stopping.max_iterations, stopping.max_seconds)
            )
            while True:
                if self._cancel.is_set():
                    status, stop_reason = "cancelled", "cancelled"
                    break
                if stopping.max_iterations is not None and len(iterations) >= (
                    stopping.max_iterations
                ):
                    stop_reason = "max_iterations"
                    break
                if stopping.max_seconds is not None and (
                    self._clock() - started >= stopping.max_seconds
                ):
                    stop_reason = "max_seconds"
                    break
                if not self._iterate(index, session, environment, iterations):
                    stop_reason = "strategy_done"
                    break
        except Exception as exc:  # one failed case run must not stop the experiment
            status, stop_reason = "error", "error"
            error = f"{type(exc).__name__}: {exc}"[:2000]
            if isinstance(exc, MedSimError):
                logger.warning("case run %s / %s failed: %s", case.case_id, key, error)
            else:
                logger.exception("case run %s / %s failed", case.case_id, key)
        return CaseRun(
            index=index,
            case_id=case.case_id,
            strategy=key,
            strategy_name=strategy.name,
            case=case,
            initial_information=initial,
            status=status,
            stop_reason=stop_reason,
            error=error,
            started_at=started_at,
            finished_at=utc_now(),
            elapsed_s=round(self._clock() - started, 2),
            iterations=iterations,
            strategy_cost_usd=round(sum(it.strategy_cost_usd for it in iterations), 6),
            environment_cost_usd=round(sum(it.environment_cost_usd for it in iterations), 6),
        )

    def _iterate(
        self,
        index: int,
        session: StrategySession,
        environment: Environment,
        iterations: list[Iteration],
    ) -> bool:
        """One question and its answer, appended to ``iterations``; False if the strategy had
        no question. An environment failure is recorded on the iteration and re-raised."""
        started_at, asked = utc_now(), self._clock()
        question = session.next_question()
        answered = self._clock()
        if question is None or not question.text.strip():
            return False
        iteration = Iteration(
            index=len(iterations) + 1,
            started_at=started_at,
            question=question.text,
            rationale=question.rationale,
            strategy_seconds=round(answered - asked, 3),
            strategy_llm_calls=question.llm_calls,
            strategy_cost_usd=calls_cost(question.llm_calls),
        )
        iterations.append(iteration)
        try:
            response = environment.query(question.text)
        except Exception as exc:
            iteration.environment_seconds = round(self._clock() - answered, 3)
            iteration.error = f"{type(exc).__name__}: {exc}"[:2000]
            self._emit("iteration_finished", index, iteration)
            raise
        iteration.environment_seconds = round(self._clock() - answered, 3)
        iteration.answer = response.output_answer
        iteration.answer_source = response.answer_source
        iteration.environment_response = compact_response(response)
        iteration.environment_cost_usd = environment_cost(response)
        session.remember(question.text, response.output_answer)
        self._emit("iteration_finished", index, iteration)
        return True

    def _emit(self, event: str, *args: Any) -> None:
        """Notify the listener; a failing listener never breaks the experiment."""
        try:
            getattr(self.listener, event)(*args)
        except Exception:
            logger.exception("experiment listener failed on %s", event)
