"""Command line: ``python scripts/run_experiment.py --config configs/basic.json``
(or ``python -m experiment`` from the project root)."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TextIO

from experiment.config import ExperimentConfig, load_config, parse_config
from experiment.progress import ProgressTracker
from experiment.record import CaseRun
from experiment.runner import PROJECT_ROOT, ExperimentRunner
from medsim.cli import RedactingFilter
from medsim.errors import ConfigError

RunnerFactory = Callable[..., ExperimentRunner]

STOP_REASONS = {
    "max_iterations": "iteration limit",
    "max_seconds": "time limit",
    "strategy_done": "strategy finished",
    "cancelled": "cancelled",
    "error": "error",
}


def format_duration(seconds: float) -> str:
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


class ConsoleProgress(ProgressTracker):
    """Prints a line per finished case run; on a terminal, also a live progress bar."""

    BAR_WIDTH = 24

    def __init__(self, stream: TextIO, *, live: bool | None = None) -> None:
        super().__init__()
        self._stream = stream
        self._live = stream.isatty() if live is None else live
        self._print_lock = threading.Lock()
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None

    def bar(self) -> str:
        snap = self.snapshot()
        filled = round(snap["fraction"] * self.BAR_WIDTH)
        parts = [
            f"[{'█' * filled}{'░' * (self.BAR_WIDTH - filled)}] {snap['fraction']:4.0%}",
            f"{snap['finished']}/{snap['total']} case runs",
            f"{snap['iterations']} iterations",
            format_duration(snap["elapsed_s"]),
        ]
        if snap["eta_s"] is not None:
            parts.append(f"~{format_duration(snap['eta_s'])} left")
        parts.append(f"${snap['cost_usd']:.4f}")
        if snap["errors"]:
            parts.append(f"{snap['errors']} errors")
        return " · ".join(parts)

    def _write(self, line: str | None = None) -> None:
        with self._print_lock:
            if self._live:
                self._stream.write("\r\033[K")
            if line is not None:
                self._stream.write(line + "\n")
            if self._live and not self._stop.is_set():
                self._stream.write(self.bar())
            self._stream.flush()

    def start(self) -> None:
        if not self._live or self._ticker is not None:
            return

        def tick() -> None:
            while not self._stop.wait(0.5):
                self._write()

        self._ticker = threading.Thread(target=tick, name="progress-bar", daemon=True)
        self._ticker.start()

    def stop(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        if self._ticker is not None:
            self._ticker.join()
        self._write()

    def case_finished(self, case_run: CaseRun) -> None:
        super().case_finished(case_run)
        line = (
            f"[{self.finished}/{self.total}] {case_run.case_id} · {case_run.strategy} · "
            f"{len(case_run.iterations)} iterations · {STOP_REASONS[case_run.stop_reason]} · "
            f"{format_duration(case_run.elapsed_s)} · ${case_run.cost_usd:.4f}"
        )
        if case_run.error:
            line += f"\n      error: {case_run.error}"
        self._write(line)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_experiment",
        description="Run an information gathering experiment: every selected case with every "
        "strategy in the config. Paths inside the config are relative to the project root.",
    )
    parser.add_argument("--config", type=Path, default=Path("configs/basic.json"),
                        help="Experiment config JSON (default: configs/basic.json).")  # fmt: skip
    parser.add_argument("--output", help="Record path; overrides the config. {name} and "
                        "{timestamp} are filled in.")  # fmt: skip
    parser.add_argument("--workers", type=int, help="Case runs in parallel; overrides the config.")
    parser.add_argument("--max-cases", type=int, help="Only the first N selected cases.")
    parser.add_argument("--max-iterations", type=int, help="Iteration limit per case run.")
    parser.add_argument("--max-seconds", type=float, help="Time limit per case run.")
    parser.add_argument("--no-verify-models", action="store_true",
                        help="Skip the OpenRouter model-slug check.")  # fmt: skip
    parser.add_argument("--verbose", action="store_true", help="Debug logging.")
    return parser


def apply_overrides(config: ExperimentConfig, args: argparse.Namespace) -> ExperimentConfig:
    data: dict[str, Any] = config.model_dump(mode="json")
    if args.output:
        data["output"] = args.output
    if args.workers is not None:
        data["workers"] = args.workers
    if args.max_cases is not None:
        data["max_cases"] = args.max_cases
    if args.max_iterations is not None:
        data["stopping"]["max_iterations"] = args.max_iterations
    if args.max_seconds is not None:
        data["stopping"]["max_seconds"] = args.max_seconds
    return parse_config(data)


def describe_plan(config: ExperimentConfig, cases: int, output: Path, workers: int) -> str:
    stopping = config.stopping
    limits = []
    if stopping.max_iterations is not None:
        limits.append(f"{stopping.max_iterations} iterations")
    if stopping.max_seconds is not None:
        limits.append(f"{stopping.max_seconds:g} s")
    strategies = ", ".join(config.strategy_keys)
    n_strategies = len(config.strategies)
    return "\n".join(
        [
            f'Experiment "{config.name}": {cases} cases x {n_strategies} '
            f"{'strategy' if n_strategies == 1 else 'strategies'} ({strategies}) = "
            f"{cases * n_strategies} case runs, {workers} in parallel.",
            f"Each case run stops after {' or '.join(limits)}, whichever comes first.",
            f"Record: {output} (finished case runs are saved as they complete).",
            "",
        ]
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    project_root: Path | None = None,
    runner_factory: RunnerFactory = ExperimentRunner,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run an experiment. With ``project_root``, paths on the command line are relative to the
    current directory and paths inside the config (and .env) to the project root."""
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    config_path: Path = args.config
    if project_root is not None:
        if not config_path.is_absolute() and not config_path.exists():
            config_path = project_root / config_path
        config_path = config_path.resolve()
        if args.output and not Path(args.output).is_absolute():
            args.output = str(Path.cwd() / args.output)
        os.chdir(project_root)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=stderr,
    )

    progress = ConsoleProgress(stdout)
    try:
        config = apply_overrides(load_config(config_path), args)
        runner = runner_factory(
            config, listener=progress, verify_models=False if args.no_verify_models else None
        )
        plan = runner.prepare()
    except ConfigError as exc:
        print(f"experiment: configuration error: {exc}", file=stderr)
        return 2
    secret = plan.settings.openrouter_api_key.get_secret_value()
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactingFilter([secret]))

    workers = min(config.workers, plan.case_runs)
    print(describe_plan(config, len(plan.cases), plan.output, workers), file=stdout)
    progress.start()
    try:
        record = runner.run()
    except KeyboardInterrupt:
        progress.stop()
        print(f"\nInterrupted. Finished case runs were saved to {plan.output}.", file=stderr)
        return 130
    finally:
        progress.stop()

    overall = record.summary["overall"]
    print(
        f"\n{record.status.capitalize()} in {format_duration(record.elapsed_s or 0)}: "
        f"{overall['case_runs']} case runs, {overall['iterations']} iterations, "
        f"{overall['errors']} errors, ${overall['cost_usd']['total']:.4f}.",
        file=stdout,
    )
    print(f"Record saved to {plan.output}", file=stdout)
    print("View it in the web app (run_webapp.command), tab View record.", file=stdout)
    return 1 if overall["errors"] else 0


def console_main() -> int:
    """Entry point for ``python -m experiment`` and the ``ics-experiment`` command."""
    return main(project_root=PROJECT_ROOT)
