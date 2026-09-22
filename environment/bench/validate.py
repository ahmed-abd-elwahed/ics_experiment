"""Step 5: check the judge.

- Controls: synthetic documents with known grades (a matching range, a far-off range, an
  off-topic study, the same study in dogs).
- Flipped truth: re-run pass 2 on "within" verdicts with the true value moved far away; the
  verdict should change. This shows the judge reads the true value.
- Second judge: re-grade a sample with a model from another family, for agreement (kappa).
- Human labels: export a stratified sample to CSV; the report scores filled-in rows.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import math
import random
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from bench.judge import RUBRIC, Judge, doc_key, latest_runs, ok_judgments
from bench.schemas import (
    ControlKind,
    ControlResult,
    DocRecord,
    FlipResult,
    Item,
    Pass1Judgment,
    Pass2Judgment,
)
from bench.text import numeric_value
from bench.workspace import JsonlWriter, Workspace, read_models

logger = logging.getLogger("bench.validate")

_CELSIUS = {"°c", "c", "ºc", "celsius", "degrees celsius"}
_FAHRENHEIT = {"°f", "f", "ºf", "fahrenheit"}
OFF_TOPIC = (
    "Among 120 adults undergoing elective cataract surgery, intraocular pressure ranged from 12 "
    "to 18 mmHg."
)
OFF_TOPIC_ALT = "Among 60 healthy adults, nightly REM sleep lasted 90 to 120 minutes."


def _fmt(x: float, like: str) -> str:
    core = like.replace(",", "")
    decimals = len(core.split(".")[1]) if "." in core else 0
    return f"{x:.{decimals}f}"


def shifted(value: float, unit: str | None) -> float:
    """A value far from ``value`` but still expressed in the same unit."""
    u = (unit or "").strip().casefold()
    if u in _CELSIUS:
        return value - 4 if value >= 36 else value + 4
    if u in _FAHRENHEIT:
        return value - 7 if value >= 97 else value + 7
    if u == "%":
        return value * 0.5 if value >= 50 else min(value * 2, 99)
    return value * 3


def bracket(value: float, unit: str | None) -> tuple[float, float]:
    u = (unit or "").strip().casefold()
    if u in _CELSIUS | _FAHRENHEIT:
        return value - 0.6, value + 0.6
    if u == "%":
        return max(value - 5, 0), min(value + 5, 100)
    return value * 0.8, value * 1.25


def control_documents(item: Item) -> dict[ControlKind, str] | None:
    """Synthetic documents for one set A item; None if its value is not a single number."""
    assert item.truth is not None
    value = numeric_value(item.truth.value)
    if value is None or value == 0:
        return None
    unit = f" {item.truth.unit}" if item.truth.unit else ""
    lo, hi = bracket(value, item.truth.unit)
    far_lo, far_hi = bracket(shifted(value, item.truth.unit), item.truth.unit)
    like = item.truth.value

    def study(who: str, a: float, b: float) -> str:
        return (
            f"Among {who} with {item.diagnosis}, {item.variable} ranged from {_fmt(a, like)} to "
            f"{_fmt(b, like)}{unit}."
        )

    off = OFF_TOPIC_ALT if "intraocular" in item.variable.casefold() else OFF_TOPIC
    return {
        "positive": study("48 patients", lo, hi),
        "far_range": study("48 patients", far_lo, far_hi),
        "off_topic": off,
        "veterinary": study("30 dogs", lo, hi),
    }


EXPECTED: dict[ControlKind, str] = {
    "positive": "relevance 3, usefulness 2, correctness 2",
    "far_range": "usefulness 2, correctness 0 or 1",
    "off_topic": "relevance 0, usefulness 0",
    "veterinary": "relevance 0, usefulness 0",
}


def _passed(kind: ControlKind, r: int | None, u: int | None, c: int | None) -> bool:
    if kind == "positive":
        return r == 3 and u == 2 and c == 2
    if kind == "far_range":
        return u == 2 and c in (0, 1)
    return r == 0 and u == 0


def run_control(judge: Judge, item: Item, kind: ControlKind, text: str) -> ControlResult:
    doc = DocRecord(rank=0, source="control", doc_id=f"CONTROL:{kind}", title=None, text=text)
    base: dict[str, Any] = {"item_id": item.item_id, "control": kind, "judge_model": judge.model,
            "rubric": RUBRIC, "document": text, "expected": EXPECTED[kind]}  # fmt: skip
    first = judge.pass1(item, doc)
    if first.status != "ok" or first.output is None:
        return ControlResult(**base, passed=None, error=first.error, llm_calls=first.llm_calls)
    calls = list(first.llm_calls)
    correctness = None
    second_output = None
    if kind in ("positive", "far_range") and (first.usefulness or 0) >= 1:
        second = judge.pass2(item, doc, first.output)
        calls += second.llm_calls
        if second.status != "ok":
            return ControlResult(**base, passed=None, error=second.error, llm_calls=calls)
        second_output, correctness = second.output, second.correctness
    return ControlResult(
        **base, passed=_passed(kind, first.relevance, first.usefulness, correctness),
        relevance=first.relevance, usefulness=first.usefulness, correctness=correctness,
        pass1=first.output, pass2=second_output, llm_calls=calls,
    )  # fmt: skip


def _sample(keys: Sequence[str], k: int, seed: int) -> list[str]:
    ranked = sorted(keys, key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    return ranked[:k]


def _docs_by_key(
    ws: Workspace, items: dict[str, Item], configs: Sequence[str]
) -> dict[str, tuple[Item, DocRecord]]:
    docs: dict[str, tuple[Item, DocRecord]] = {}
    for per_item in latest_runs(ws, configs).values():
        for item_id, run in per_item.items():
            if item_id in items:
                for doc in run.documents:
                    docs.setdefault(doc_key(item_id, doc.doc_id, doc.text), (items[item_id], doc))
    return docs


def run_validate(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[str],
    judge: Judge,
    *,
    second_judge: Judge | None,
    controls: int = 10,
    flips: int = 10,
    second_fraction: float = 0.1,
    export_human: int = 0,
    seed: int = 7,
    workers: int = 8,
) -> dict[str, Any]:
    by_id = {i.item_id: i for i in items}
    summary: dict[str, Any] = {}
    pool = ThreadPoolExecutor(max_workers=max(1, workers))

    # Controls.
    done = {(c.item_id, c.control) for c in read_models(ws.controls, ControlResult)
            if c.judge_model == judge.model and c.passed is not None}  # fmt: skip
    eligible = [i for i in items if i.truth is not None and control_documents(i)]
    chosen = [by_id[k] for k in _sample([i.item_id for i in eligible], controls, seed)]
    tasks = [
        (item, kind, text)
        for item in chosen
        for kind, text in (control_documents(item) or {}).items()
        if (item.item_id, kind) not in done
    ]
    writer = JsonlWriter(ws.controls)
    for result in pool.map(lambda t: run_control(judge, *t), tasks):
        writer.write(result)
    summary["controls_run"] = len(tasks)

    # Flipped truth.
    pass1 = ok_judgments(ws.pass1, Pass1Judgment, judge.model)
    pass2 = ok_judgments(ws.pass2, Pass2Judgment, judge.model)
    docs = _docs_by_key(ws, by_id, configs)
    flipped_done = {
        f.doc_key for f in read_models(ws.flips, FlipResult) if f.judge_model == judge.model
    }

    def numeric_truth(key: str) -> bool:
        truth = docs[key][0].truth
        return truth is not None and numeric_value(truth.value) is not None

    within = [
        key
        for key, j in pass2.items()
        if j.output
        and j.output.verdict == "within"
        and key in docs
        and key in pass1
        and numeric_truth(key)
    ]
    flip_keys = [k for k in _sample(within, flips, seed) if k not in flipped_done]

    def flip(key: str) -> FlipResult:
        item, doc = docs[key]
        assert item.truth is not None and pass1[key].output is not None
        value = numeric_value(item.truth.value)
        assert value is not None
        unit = f" {item.truth.unit}" if item.truth.unit else ""
        truth = f"{_fmt(shifted(value, item.truth.unit), item.truth.value)}{unit}"
        result = judge.pass2(item, doc, pass1[key].output, truth=truth)
        verdict = result.output.verdict if result.output else None
        return FlipResult(
            doc_key=key, item_id=item.item_id, judge_model=judge.model, rubric=RUBRIC,
            original_verdict="within", flipped_truth=truth, new_verdict=verdict,
            passed=None if verdict is None else verdict != "within", error=result.error,
            llm_calls=result.llm_calls,
        )  # fmt: skip

    flip_writer = JsonlWriter(ws.flips)
    for flipped in pool.map(flip, flip_keys):
        flip_writer.write(flipped)
    summary["flips_run"] = len(flip_keys)

    # Second judge.
    if second_judge is not None and second_fraction > 0:
        done1 = ok_judgments(ws.second_pass1, Pass1Judgment, second_judge.model)
        keys = [k for k in pass1 if k in docs]
        sample1 = [k for k in _sample(keys, math.ceil(second_fraction * len(keys)), seed)
                   if k not in done1]  # fmt: skip
        writer1 = JsonlWriter(ws.second_pass1)
        for judged1 in pool.map(lambda k: second_judge.pass1(*docs[k]), sample1):
            writer1.write(judged1)
        done1 = ok_judgments(ws.second_pass1, Pass1Judgment, second_judge.model)
        done2 = ok_judgments(ws.second_pass2, Pass2Judgment, second_judge.model)
        keys2 = [k for k in pass2 if k in docs and k in pass1]
        sample2 = [k for k in _sample(keys2, math.ceil(second_fraction * len(keys2)), seed)
                   if k not in done2]  # fmt: skip

        def second_pass2(key: str) -> Pass2Judgment:
            evidence = (done1[key].output if key in done1 else None) or pass1[key].output
            assert evidence is not None
            return second_judge.pass2(*docs[key], evidence)

        writer2 = JsonlWriter(ws.second_pass2)
        for judged2 in pool.map(second_pass2, sample2):
            writer2.write(judged2)
        summary["second_judge"] = {"pass1": len(sample1), "pass2": len(sample2)}
    pool.shutdown()

    if export_human > 0:
        summary["human_rows"] = write_human_sample(ws, docs, pass1, export_human, seed)
    return summary


HUMAN_COLUMNS = [
    "doc_key", "item_id", "question", "variable", "diagnosis", "patient", "true_value",
    "title", "text", "human_relevance_0_3", "human_usefulness_0_2", "human_correctness_0_2",
    "notes",
]  # fmt: skip


def write_human_sample(
    ws: Workspace,
    docs: dict[str, tuple[Item, DocRecord]],
    pass1: dict[str, Pass1Judgment],
    n: int,
    seed: int,
) -> int:
    """A sample stratified by the judge's relevance grade, without the judge's grades."""
    by_grade: dict[int, list[str]] = {}
    for key, judged in pass1.items():
        if key in docs and judged.relevance is not None:
            by_grade.setdefault(judged.relevance, []).append(key)
    rng = random.Random(seed)
    for keys in by_grade.values():
        rng.shuffle(keys)
    picked: list[str] = []
    while len(picked) < n and any(by_grade.values()):
        for grade in sorted(by_grade):
            if by_grade[grade] and len(picked) < n:
                picked.append(by_grade[grade].pop())
    ws.human_csv.parent.mkdir(parents=True, exist_ok=True)
    with ws.human_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HUMAN_COLUMNS)
        writer.writeheader()
        for key in picked:
            item, doc = docs[key]
            truth = f"{item.truth.value} {item.truth.unit or ''}".strip() if item.truth else ""
            writer.writerow({
                "doc_key": key, "item_id": item.item_id, "question": item.question,
                "variable": item.variable, "diagnosis": item.diagnosis, "patient": item.patient,
                "true_value": truth, "title": doc.title or "", "text": doc.text,
            })  # fmt: skip
    return len(picked)


def read_human_labels(ws: Workspace) -> list[dict[str, str]]:
    if not ws.human_csv.exists():
        return []
    with ws.human_csv.open(encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("human_relevance_0_3", "").strip()]
