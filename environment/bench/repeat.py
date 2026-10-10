"""Repeated runs: the same questions, the same configurations, run again, for run-to-run spread.

Layout under ``root`` (default ``environment/results/repeats``)::

    index.json                 which workspaces hold run 1..N, and how the repeats were made
    run_02/sets_ab/            a workspace: sets A and B (the retrieval configurations)
    run_02/set_c/              a workspace: set C (case_information)
    ...
    run_10/...

Every repeat workspace starts from copies of the source workspaces' questions (``items.jsonl``,
``facts.jsonl``, ``rejected_items.jsonl``), so every run answers exactly the same questions.
Run 1 is the source workspaces themselves (referenced in ``index.json``, not copied). All runs'
questions share one thread pool, one HTTP client, and one LitSense rate limiter (1 request/s),
and are ordered run by run, so a stopped repeat leaves whole runs behind; rerunning resumes.
Judging and reports then run per workspace (``judge``, ``report``).
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bench.run import FullTextFactory, RetrieverFactory, RunConfig, run_one
from bench.schemas import Item, RunRecord
from bench.workspace import JsonlWriter, Workspace, latest_by, read_models, update_manifest
from medsim.config import Settings
from medsim.llm.base import LLMClient

logger = logging.getLogger("bench.repeat")

QUESTION_FILES = ("items.jsonl", "facts.jsonl", "rejected_items.jsonl")


def run_workspaces(root: Path, run: int) -> tuple[Workspace, Workspace]:
    base = root / f"run_{run:02d}"
    return Workspace(base / "sets_ab"), Workspace(base / "set_c")


def prepare(source: Workspace, target: Workspace, run: int) -> None:
    """Copy the source's questions into a new repeat workspace (once)."""
    target.root.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in QUESTION_FILES:
        if (source.root / name).exists() and not (target.root / name).exists():
            shutil.copy2(source.root / name, target.root / name)
            copied.append(name)
    if copied:
        update_manifest(target, "questions", {"run": run, "copied_from": str(source.root),
                                              "files": copied})  # fmt: skip


def write_index(
    root: Path, runs: Sequence[int], source_ab: Workspace, source_c: Workspace,
    configs_ab: Sequence[str], configs_c: Sequence[str], search_cache: bool,
) -> None:  # fmt: skip
    path = root / "index.json"
    index: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    index.setdefault("description", "Repeated runs of the benchmark on the same questions; "
                     "run 1 is the original evaluation.")  # fmt: skip
    index.setdefault("runs", {})["1"] = {
        "sets_ab": str(source_ab.root),
        "set_c": str(source_c.root),
    }
    for run in runs:
        ab, c = run_workspaces(root, run)
        index["runs"][str(run)] = {"sets_ab": str(ab.root), "set_c": str(c.root)}
    index["configs_ab"] = sorted(set(index.get("configs_ab", [])) | set(configs_ab))
    index["configs_c"] = sorted(set(index.get("configs_c", [])) | set(configs_c))
    index["search_cache"] = search_cache
    index.setdefault("history", []).append({
        "at": datetime.now(UTC).isoformat(timespec="seconds"), "runs": list(runs),
        "configs_ab": list(configs_ab), "configs_c": list(configs_c),
    })  # fmt: skip
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def run_repeats(
    root: Path,
    runs: Sequence[int],
    *,
    source_ab: Workspace,
    source_c: Workspace,
    configs_ab: Sequence[RunConfig],
    configs_c: Sequence[RunConfig],
    llm: LLMClient,
    base_settings: Settings,
    retrievers: RetrieverFactory,
    fulltext: FullTextFactory | None = None,
    workers: int = 24,
    search_cache: bool = False,
) -> dict[str, Any]:
    """Every (run, configuration, question) not yet answered successfully, in one pool."""
    write_index(root, runs, source_ab, source_c, [c.name for c in configs_ab],
                [c.name for c in configs_c], search_cache)  # fmt: skip
    todo: list[tuple[int, Workspace, RunConfig, Item]] = []
    writers: dict[tuple[Path, str], JsonlWriter] = {}
    for run in runs:
        ab, c = run_workspaces(root, run)
        for source, ws, configs in ((source_ab, ab, configs_ab), (source_c, c, configs_c)):
            if not configs:
                continue
            prepare(source, ws, run)
            items = read_models(ws.items, Item)
            for config in configs:
                writers[(ws.root, config.name)] = JsonlWriter(ws.run_file(config.name))
                latest = latest_by(
                    read_models(ws.run_file(config.name), RunRecord), lambda r: r.item_id
                )
                done = {k for k, r in latest.items() if r.status == "ok"}
                todo += [(run, ws, config, i) for i in items if i.item_id not in done]
    counts: dict[str, Counter[str]] = {}
    started = time.perf_counter()
    out_of_credit = threading.Event()

    def work(config: RunConfig, item: Item) -> RunRecord | None:
        if out_of_credit.is_set():  # do not queue up thousands of refused calls
            return None
        return run_one(
            item, config, llm=llm, base_settings=base_settings, retrievers=retrievers,
            fulltext=fulltext,
        )  # fmt: skip

    skipped = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(work, config, item): (run, ws) for run, ws, config, item in todo}
        for n, future in enumerate(as_completed(futures), 1):
            run, ws = futures[future]
            record = future.result()
            if record is None:
                skipped += 1
                continue
            if record.status != "ok" and "HTTP 402" in (record.error or ""):
                if not out_of_credit.is_set():
                    logger.error("OpenRouter reports insufficient credits; stopping the repeat")
                out_of_credit.set()
                skipped += 1  # not recorded: nothing ran; a rerun picks it up
                continue
            writers[(ws.root, record.config)].write(record)
            key = f"run_{run:02d}/{record.config}"
            counts.setdefault(key, Counter())[record.status] += 1
            spent = record.retrieval_cost_usd + sum(record.llm_cost_usd.values())
            logger.info(
                "repeat run %d %s %s: %s %s, %.1fs, $%.4f [%d/%d]", run, record.config,
                record.item_id, record.status, record.path or record.error, record.wall_time_s,
                spent, n, len(todo),
            )  # fmt: skip
    for run in runs:
        for ws in run_workspaces(root, run):
            if ws.root.exists():
                done_here = {
                    k: dict(v) for k, v in counts.items() if k.startswith(f"run_{run:02d}/")
                }
                update_manifest(ws, "repeat_run", {"run": run, "results": done_here})
    return {"todo": len(todo), "stopped_out_of_credit": out_of_credit.is_set(),
            "not_run": skipped, "elapsed_s": round(time.perf_counter() - started, 1),
            **{k: dict(v) for k, v in counts.items()}}  # fmt: skip
