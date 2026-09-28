"""Step 5: check the judge panel.

- Controls: synthetic set A answers with known verdicts (the true value itself, and a value far
  from it), judged by the whole panel; pass/fail is decided on the voted label.
- Flipped truth: re-judge answers the panel voted "exact" with the true value moved far away, in
  the full case too; the voted label should change. This shows the judges read the true value.
- Panel agreement (how often the judges agree) needs no extra calls; the report computes it.
- Human labels: export a stratified sample to CSV; the report compares them with the voted label.

Every judge call sees the full case, as in the judge step. All panel calls of the controls and
the flips run in one thread pool.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import random
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from bench.judge import (
    RUBRIC,
    Judge,
    Vote,
    answer_key,
    full_cases,
    judgeable,
    latest_runs,
    panel_judgments,
    panel_votes,
)
from bench.schemas import (
    ConsistencyJudgment,
    ControlKind,
    ControlResult,
    FlipResult,
    Item,
    MaskedCorrectnessJudgment,
)
from bench.text import numeric_value, value_pattern
from bench.workspace import JsonlWriter, Workspace, read_models
from medsim.models import CaseStudy

logger = logging.getLogger("bench.validate")

_CELSIUS = {"°c", "c", "ºc", "celsius", "degrees celsius"}
_FAHRENHEIT = {"°f", "f", "ºf", "fahrenheit"}


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


def control_answers(item: Item) -> dict[ControlKind, str] | None:
    """Synthetic answers for one set A item; None if its value is not a single number."""
    assert item.truth is not None
    value = numeric_value(item.truth.value)
    if value is None or value == 0:
        return None
    unit = f" {item.truth.unit}" if item.truth.unit else ""
    far = _fmt(shifted(value, item.truth.unit), item.truth.value)
    return {
        "true_value": f"The patient's {item.variable} was {item.truth.value}{unit}.",
        "far_value": f"The patient's {item.variable} was {far}{unit}.",
    }


EXPECTED: dict[ControlKind, str] = {
    "true_value": "exact",
    "far_value": "same_category or different_category",
}


def _panel_result(
    judged: Sequence[MaskedCorrectnessJudgment], panel: Sequence[str]
) -> dict[str, Any]:
    """The panel's vote on one answer's judgments, with each judge's verdict and error."""
    by_model = {j.judge_model: j for j in judged}
    result: Vote = panel_votes(by_model, panel)
    return {
        "votes": result.votes,
        "verdict": result.label,
        "resolution": result.resolution,
        "outputs": {m: j.output for m, j in by_model.items() if j.output is not None},
        "errors": {m: j.error or "error" for m, j in by_model.items() if j.status != "ok"},
        "llm_calls": [c for j in judged for c in j.llm_calls],
    }


def control_result(
    item: Item, kind: ControlKind, answer: str, judged: Sequence[MaskedCorrectnessJudgment],
    panel: Sequence[str],
) -> ControlResult:  # fmt: skip
    fields = _panel_result(judged, panel)
    verdict = fields["verdict"]
    expected = ("exact",) if kind == "true_value" else ("same_category", "different_category")
    return ControlResult(
        item_id=item.item_id, control=kind, judges=list(panel), rubric=RUBRIC, answer=answer,
        expected=EXPECTED[kind], passed=None if verdict is None else verdict in expected,
        **fields,
    )  # fmt: skip


def _sample(keys: Sequence[str], k: int, seed: int) -> list[str]:
    ranked = sorted(keys, key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    return ranked[:k]


Answer = tuple[Item, str, str]  # item, config, generated answer


def answers_by_key(
    ws: Workspace, items: dict[str, Item], configs: Sequence[str]
) -> dict[str, Answer]:
    answers: dict[str, Answer] = {}
    for config, per_item in latest_runs(ws, configs).items():
        for item_id, run in per_item.items():
            if item_id in items and judgeable(run):
                answer = run.output_answer or ""
                answers[answer_key(item_id, config, answer)] = (items[item_id], config, answer)
    return answers


def run_validate(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[str],
    panel: Sequence[Judge],
    *,
    cases: Mapping[str, CaseStudy],
    controls: int = 10,
    flips: int = 10,
    export_human: int = 0,
    seed: int = 7,
    workers: int = 8,
) -> dict[str, Any]:
    by_id = {i.item_id: i for i in items}
    full = full_cases(items, cases)
    models = [j.model for j in panel]
    summary: dict[str, Any] = {"panel": models}

    # Controls: which (item, control) pairs still need a panel verdict.
    done = {(c.item_id, c.control) for c in read_models(ws.controls, ControlResult)
            if c.judges == models and c.rubric == RUBRIC and c.passed is not None}  # fmt: skip
    eligible = [i for i in items if i.truth is not None and control_answers(i)]
    chosen = [by_id[k] for k in _sample([i.item_id for i in eligible], controls, seed)]
    control_tasks = [
        (item, kind, text)
        for item in chosen
        for kind, text in (control_answers(item) or {}).items()
        if (item.item_id, kind) not in done
    ]

    # Flipped truth: answers the panel voted exact.
    masked = panel_judgments(ws.masked_correctness, MaskedCorrectnessJudgment, models)
    consistency = panel_judgments(ws.consistency, ConsistencyJudgment, models)
    answers = answers_by_key(ws, by_id, configs)
    flipped_done = {f.answer_key for f in read_models(ws.flips, FlipResult)
                    if f.judges == models and f.rubric == RUBRIC}  # fmt: skip

    def flippable(key: str) -> bool:
        item = answers[key][0]
        truth = item.truth
        return (
            truth is not None
            and numeric_value(truth.value) is not None
            and truth.span in full[item.item_id].narrative
            and value_pattern(truth.value).search(truth.span) is not None
        )

    exact = [
        key
        for key, judged in masked.items()
        if panel_votes(judged, models).label == "exact" and key in answers and flippable(key)
    ]
    flip_tasks = []
    for key in _sample(exact, flips, seed):
        if key in flipped_done:
            continue
        item, config, answer = answers[key]
        assert item.truth is not None
        value = numeric_value(item.truth.value)
        assert value is not None
        unit = f" {item.truth.unit}" if item.truth.unit else ""
        moved = _fmt(shifted(value, item.truth.unit), item.truth.value)
        span = value_pattern(item.truth.value).sub(moved, item.truth.span, count=1)
        truth = f'{moved}{unit} (case report: "{span}")'
        case = full[item.item_id]
        case = case.model_copy(update={"narrative": case.narrative.replace(item.truth.span, span)})
        flip_tasks.append((key, item, case, config, answer, truth))

    # Every (task, judge) pair is one job; controls and flips share one pool.
    jobs: list[tuple[str, int, Judge]] = [
        *(("control", i, judge) for i in range(len(control_tasks)) for judge in panel),
        *(("flip", i, judge) for i in range(len(flip_tasks)) for judge in panel),
    ]

    def run(job: tuple[str, int, Judge]) -> MaskedCorrectnessJudgment:
        kind, i, judge = job
        if kind == "control":
            item, _, text = control_tasks[i]
            return judge.masked_correctness(item, full[item.item_id], "control", text)
        _, item, case, config, answer, truth = flip_tasks[i]
        return judge.masked_correctness(item, case, config, answer, truth=truth)

    grouped: dict[tuple[str, int], list[MaskedCorrectnessJudgment]] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for job, judged in zip(jobs, pool.map(run, jobs), strict=True):
            grouped.setdefault((job[0], job[1]), []).append(judged)

    control_writer = JsonlWriter(ws.controls)
    for i, (item, kind, text) in enumerate(control_tasks):
        control_writer.write(control_result(item, kind, text, grouped[("control", i)], models))
    flip_writer = JsonlWriter(ws.flips)
    for i, (key, item, _, _, _, truth) in enumerate(flip_tasks):
        fields = _panel_result(grouped[("flip", i)], models)
        verdict = fields.pop("verdict")
        fields.pop("outputs")
        flip_writer.write(FlipResult(
            answer_key=key, item_id=item.item_id, judges=models, rubric=RUBRIC,
            original_verdict="exact", flipped_truth=truth, new_verdict=verdict,
            passed=None if verdict is None else verdict != "exact", **fields,
        ))  # fmt: skip
    summary["controls_run"] = len(control_tasks)
    summary["flips_run"] = len(flip_tasks)

    if export_human > 0:
        summary["human_rows"] = write_human_sample(
            ws, answers, full, masked, consistency, models, export_human, seed
        )
    return summary


HUMAN_COLUMNS = [
    "answer_key", "item_id", "question_set", "question", "variable", "diagnosis", "true_value",
    "case", "answer", "human_masked_verdict", "human_consistency", "notes",
]  # fmt: skip


def write_human_sample(
    ws: Workspace,
    answers: dict[str, Answer],
    full: dict[str, CaseStudy],
    masked: dict[str, dict[str, MaskedCorrectnessJudgment]],
    consistency: dict[str, dict[str, ConsistencyJudgment]],
    panel: Sequence[str],
    n: int,
    seed: int,
) -> int:
    """A sample stratified by question set and the panel's voted label, without the labels.

    Set A rows need human_masked_verdict (exact / same_category / different_category /
    not_comparable); set B rows need human_consistency (consistent / inconsistent).
    """
    strata: dict[tuple[str, str], list[str]] = {}
    judgments: list[tuple[str, Any]] = [*masked.items(), *consistency.items()]
    for key, judged in judgments:
        label = panel_votes(judged, panel).label
        if key in answers and label is not None:
            qs = answers[key][0].question_set
            strata.setdefault((qs, label), []).append(key)
    rng = random.Random(seed)
    for keys in strata.values():
        keys.sort()
        rng.shuffle(keys)
    picked: list[str] = []
    while len(picked) < n and any(strata.values()):
        for stratum in sorted(strata):
            if strata[stratum] and len(picked) < n:
                picked.append(strata[stratum].pop())
    ws.human_csv.parent.mkdir(parents=True, exist_ok=True)
    with ws.human_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HUMAN_COLUMNS)
        writer.writeheader()
        for key in picked:
            item, _, answer = answers[key]
            truth = f"{item.truth.value} {item.truth.unit or ''}".strip() if item.truth else ""
            writer.writerow({
                "answer_key": key, "item_id": item.item_id, "question_set": item.question_set,
                "question": item.question, "variable": item.variable,
                "diagnosis": item.diagnosis, "true_value": truth,
                "case": full[item.item_id].narrative,
                "answer": answer,
            })  # fmt: skip
    return len(picked)


def read_human_labels(ws: Workspace) -> list[dict[str, str]]:
    if not ws.human_csv.exists():
        return []
    with ws.human_csv.open(encoding="utf-8") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row.get("human_masked_verdict", "").strip()
            or row.get("human_consistency", "").strip()
        ]
