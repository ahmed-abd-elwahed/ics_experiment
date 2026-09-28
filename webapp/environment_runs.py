"""Stored evaluation runs of the simulated environment, in one shape for the viewer.

Two kinds are stored:

- medsim runs (``environment/runs/*.json``): questions asked of a case during the environment's
  live checks, each with the full ``EnvironmentResponse``.
- retrieval benchmark runs (``environment/results/<workspace>/runs/<method>.jsonl``): every
  benchmark question answered with one retrieval method, joined with the question set (the
  hidden value, for set A) and the judge's verdict on the answer: masked correctness for set A,
  factual consistency for set B.

Both become sessions, one per case, each a list of questions with the environment's response.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from bench.config import BenchSettings
from bench.judge import SET_METRICS, answer_key, panel_judgments, panel_votes
from bench.schemas import (
    ConsistencyJudgment,
    DocRecord,
    Item,
    MaskedCorrectnessJudgment,
    RunRecord,
)
from bench.workspace import Workspace, latest_by, read_jsonl, read_models
from medsim.case_study import load_cases

FORMAT = "ics-environment-runs"


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _medsim_files(root: Path) -> list[Path]:
    return sorted((root / "environment" / "runs").glob("*.json"))


def _benchmark_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for workspace in sorted((root / "environment" / "results").iterdir()):
        if (workspace / "items.jsonl").is_file():
            files.extend(sorted((workspace / "runs").glob("*.jsonl")))
    return files


def list_environment_runs(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in _medsim_files(root):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entries.append(
            {
                "path": _relative(path, root),
                "kind": "medsim_runs",
                "name": path.stem,
                "questions": len(data.get("runs") or []),
                "generated_at": data.get("generated_at"),
            }
        )
    for path in _benchmark_files(root):
        workspace = path.parent.parent
        entries.append(
            {
                "path": _relative(path, root),
                "kind": "retrieval_benchmark",
                "name": f"{workspace.name} · {path.stem}",
                "questions": len({r.get("item_id") for r in read_jsonl(path)}),
                "generated_at": None,
            }
        )
    return entries


def is_environment_run(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    return resolved in {p.resolve() for p in (*_medsim_files(root), *_benchmark_files(root))}


def load_environment_runs(path: Path, root: Path) -> dict[str, Any]:
    if path.suffix == ".jsonl":
        return _benchmark_runs(path, root)
    return _medsim_runs(path, root)


# --- medsim runs --------------------------------------------------------------------------------


def _case_from_file(root: Path, case_file: str | None, case_id: str) -> dict[str, Any] | None:
    if not case_file:
        return None
    path = root / case_file
    try:
        case = load_cases(path).get(case_id)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return case.model_dump(mode="json") if case else None


def _cost(response: dict[str, Any] | None) -> float:
    calls = (response or {}).get("llm_calls") or []
    return sum(float(call.get("cost_usd") or 0.0) for call in calls)


def _medsim_runs(path: Path, root: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    embedded = data.get("case_study")
    sessions: dict[str, dict[str, Any]] = {}
    for run in data.get("runs") or []:
        given = run.get("input") or {}
        output = run.get("output")
        case_id = str(given.get("case_id") or (embedded or {}).get("case_id") or "unknown")
        session = sessions.get(case_id)
        if session is None:
            if embedded and embedded.get("case_id") == case_id:
                case = embedded
            else:
                case = _case_from_file(root, given.get("case_file"), case_id)
            session = sessions[case_id] = {
                "case_id": case_id, "case": case, "note": None, "questions": [],
            }  # fmt: skip
        session["questions"].append(
            {
                "label": run.get("label"),
                "question": given.get("query") or (output or {}).get("input_query") or "",
                "started_at": run.get("started_at"),
                "seconds": run.get("wall_time_s"),
                "status": "ok" if output else "error",
                "error": run.get("error"),
                "response": output,
                "cost_usd": _cost(output),
            }
        )
    return {
        "format": FORMAT,
        "kind": "medsim_runs",
        "name": path.stem,
        "source": _relative(path, root),
        "generated_at": data.get("generated_at"),
        "model": data.get("model"),
        "description": "Questions asked of the environment in its live checks, each with the "
        "full environment response.",
        "sessions": list(sessions.values()),
    }


# --- retrieval benchmark runs -------------------------------------------------------------------


def _document(doc: DocRecord) -> dict[str, Any]:
    return {
        "source": doc.source,
        "doc_id": doc.doc_id,
        "title": doc.title,
        "text": doc.text,
        "full_text": doc.full_text,
        "url": doc.url,
        "journal": doc.journal,
        "pub_year": doc.pub_year,
    }


def _response(item: Item, run: RunRecord) -> dict[str, Any]:
    """The run record as an ``EnvironmentResponse``-shaped dict."""
    searched = bool(run.documents or run.literature_query or run.query_attempts)
    result = None
    if searched:
        result = {
            "query": run.literature_query or "",
            "documents": [_document(doc) for doc in run.documents],
            "per_source_counts": dict(Counter(doc.source for doc in run.documents)),
            "errors": run.source_errors,
            "latency_ms": 0,
        }
    return {
        "input_query": item.question,
        "output_answer": run.output_answer or "",
        "literature_search": searched,
        "literature_search_result": result,
        "retriever_parameters": {
            "multi_part": False,
            "path": run.path,
            "per_source": {s: {"query_attempts": a} for s, a in run.query_attempts.items()},
            "failed_sources": run.failed_sources,
            "excluded_source_docs": run.excluded_source_docs,
            **run.retrieval_notes,
        },
        "used_llm": ", ".join(dict.fromkeys(call.model for call in run.llm_calls)),
        "answer_source": run.answer_source or "unanswerable",
        "evidence": run.evidence,
        "confidence": run.confidence or "low",
        "llm_calls": [call.model_dump(mode="json") for call in run.llm_calls],
    }


def _benchmark_runs(path: Path, root: Path) -> dict[str, Any]:
    ws = Workspace(path.parent.parent)
    method = path.stem
    items = latest_by(read_models(ws.items, Item), lambda i: i.item_id)
    runs = latest_by(read_models(path, RunRecord), lambda r: r.item_id)
    panel = BenchSettings().judge_models
    masked = panel_judgments(ws.masked_correctness, MaskedCorrectnessJudgment, panel)
    consistency = panel_judgments(ws.consistency, ConsistencyJudgment, panel)

    sessions: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items.values():
        run = runs.get(item.item_id)
        if run is None:
            continue
        key = answer_key(item.item_id, method, run.output_answer or "")
        verdicts = []  # per metric: the panel's label, and each judge's own verdict
        for metric in SET_METRICS[item.question_set]:
            judged: dict[str, Any] = (
                masked if metric == "masked_correctness" else consistency
            ).get(key, {})
            voted = panel_votes(judged, panel)
            if voted.label is None:
                continue
            verdicts.append({
                "metric": metric,
                "verdict": voted.label,
                "resolution": voted.resolution,
                "judges": [
                    {"judge_model": model, **j.output.model_dump(mode="json")}
                    if (j := judged.get(model)) and j.output
                    else {"judge_model": model, "verdict": None}
                    for model in panel
                ],
            })  # fmt: skip
        note = {
            "A": "Set A: the value this question asks for was removed from the case text.",
            "B": "Set B: the case never states the value this question asks for.",
            "C": "Set C: the case states the answer; the environment answers without retrieval.",
        }[item.question_set]
        session = sessions.setdefault(
            (item.case_id, item.question_set),
            {
                "case_id": item.case_id,
                "case": item.case.model_dump(mode="json"),
                "note": note,
                "questions": [],
            },
        )
        session["questions"].append(
            {
                "label": item.item_id,
                "question": item.question,
                "started_at": run.started_at,
                "seconds": run.wall_time_s,
                "status": run.status,
                "error": run.error,
                "response": _response(item, run) if run.status == "ok" else None,
                "cost_usd": run.retrieval_cost_usd + sum(run.llm_cost_usd.values()),
                "truth": item.truth.model_dump(mode="json") if item.truth else None,
                "removed_text": item.removed_text,
                "answer_verdicts": verdicts,
                "meta": {
                    "question_set": item.question_set,
                    "variable": item.variable,
                    "category": item.category,
                    "method": method,
                    "judge_panel": panel,
                },
            }
        )
    return {
        "format": FORMAT,
        "kind": "retrieval_benchmark",
        "name": f"{ws.root.name} · {method}",
        "source": _relative(path, root),
        "generated_at": None,
        "model": None,
        "description": f"Retrieval benchmark questions answered with the {method} method. "
        f"Answers are graded by a panel of {len(panel)} judges ({', '.join(panel)}); the label "
        f"shown is their majority vote.",
        "sessions": list(sessions.values()),
    }
