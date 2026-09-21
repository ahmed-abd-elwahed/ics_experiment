"""Workspace layout, append-only JSONL files, and the run manifest."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger("bench")

M = TypeVar("M", bound=BaseModel)


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    @property
    def facts(self) -> Path:
        return self.root / "facts.jsonl"

    @property
    def items(self) -> Path:
        return self.root / "items.jsonl"

    @property
    def rejected(self) -> Path:
        return self.root / "rejected_items.jsonl"

    def run_file(self, config: str) -> Path:
        return self.root / "runs" / f"{config}.jsonl"

    def run_configs(self) -> list[str]:
        return sorted(p.stem for p in (self.root / "runs").glob("*.jsonl"))

    @property
    def pass1(self) -> Path:
        return self.root / "judge" / "pass1.jsonl"

    @property
    def pass2(self) -> Path:
        return self.root / "judge" / "pass2.jsonl"

    @property
    def answers(self) -> Path:
        return self.root / "judge" / "answers.jsonl"

    @property
    def controls(self) -> Path:
        return self.root / "validate" / "controls.jsonl"

    @property
    def flips(self) -> Path:
        return self.root / "validate" / "flips.jsonl"

    @property
    def second_pass1(self) -> Path:
        return self.root / "validate" / "second_pass1.jsonl"

    @property
    def second_pass2(self) -> Path:
        return self.root / "validate" / "second_pass2.jsonl"

    @property
    def human_csv(self) -> Path:
        return self.root / "validate" / "human_labels.csv"

    @property
    def report_md(self) -> Path:
        return self.root / "report.md"

    @property
    def report_json(self) -> Path:
        return self.root / "report.json"


class JsonlWriter:
    """Thread-safe append-only writer; each record is flushed as one line."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, record: BaseModel | dict[str, Any]) -> None:
        data = record.model_dump(mode="json") if isinstance(record, BaseModel) else record
        line = json.dumps(data, ensure_ascii=False)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """All records; a line cut short by a crash is skipped with a warning."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("%s:%d is not valid JSON; skipped", path, number)
    return records


def read_models(path: Path, model: type[M]) -> list[M]:
    return [model.model_validate(r) for r in read_jsonl(path)]


def latest_by(records: Iterable[M], key: Callable[[M], Any]) -> dict[Any, M]:
    """Later records replace earlier ones with the same key (reruns append)."""
    latest: dict[Any, M] = {}
    for record in records:
        latest[key(record)] = record
    return latest


def load_manifest(ws: Workspace) -> dict[str, Any]:
    if not ws.manifest.exists():
        return {}
    data: dict[str, Any] = json.loads(ws.manifest.read_text(encoding="utf-8"))
    return data


def update_manifest(ws: Workspace, step: str, data: dict[str, Any]) -> None:
    """Append a step entry (parameters, spend) to the manifest's history."""
    manifest = load_manifest(ws)
    entry = {"step": step, "at": datetime.now(UTC).isoformat(timespec="seconds"), **data}
    manifest.setdefault("steps", []).append(entry)
    manifest.setdefault("latest", {})[step] = entry
    ws.root.mkdir(parents=True, exist_ok=True)
    ws.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
