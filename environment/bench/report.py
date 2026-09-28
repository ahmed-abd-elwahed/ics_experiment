"""Step 6: turn judgments into per-question scores, compare configurations, write the report."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from bench.judge import (
    RUBRIC,
    SET_METRICS,
    answer_key,
    judgeable,
    latest_runs,
    panel_judgments,
    panel_votes,
)
from bench.run import CONFIGS, RETRIEVAL_STAGES
from bench.schemas import (
    CaseFacts,
    ConsistencyJudgment,
    ControlResult,
    FlipResult,
    Item,
    MaskedCorrectnessJudgment,
    RejectedItem,
    RunRecord,
    calls_cost,
)
from bench.stats import Estimate, cluster_bootstrap, cohen_kappa
from bench.validate import read_human_labels
from bench.workspace import Workspace, load_manifest, read_models


@dataclass
class Score:
    """One question under one configuration (a question whose run is missing or failed is kept,
    unlabelled, so every label's share is over the full question set)."""

    item_id: str
    config: str
    question_set: str
    diagnosis: str
    category: str
    characteristic: bool | None
    path: str | None
    n_docs: int
    has_answer: bool  # medsim generated an answer, so the judge grades it
    ran: bool = True  # False: no successful run for this question under this configuration
    truth_category: str | None = None
    # The panel's voted label (the one the metrics count), and each judge's own label.
    masked_verdict: str | None = None  # set A: exact / same_category / different_category / ...
    consistency: str | None = None  # set B: consistent / inconsistent with the full case
    # Per metric (masked_correctness, factual_consistency): judge model -> label, and how the
    # vote went (unanimous / majority / tie_break_main_judge / tie_break_next_judge).
    votes: dict[str, dict[str, str | None]] = field(default_factory=dict)
    resolution: dict[str, str | None] = field(default_factory=dict)
    excluded_source_docs: int = 0
    retrieval_cost: float = 0.0
    stage_cost: dict[str, float] = field(default_factory=dict)
    wall_time_s: float = 0.0
    llm_time_s: float = 0.0  # medsim's own LLM calls (Stages A-C); the rest is mostly retrieval

    @property
    def pipeline_cost(self) -> float:
        return sum(self.stage_cost.values())

    @property
    def total_cost(self) -> float:
        return self.retrieval_cost + self.pipeline_cost


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _ran(value: Callable[[Score], float]) -> Callable[[Score], float | None]:
    """A run statistic (documents, cost, time): undefined for questions that did not run."""
    return lambda s: value(s) if s.ran else None


def _label(field_name: str, label: str | None) -> Callable[[Score], float]:
    """1 if the judge gave this question this label, else 0 (None = no label)."""
    return lambda s: float(getattr(s, field_name) == label)


def _label_metrics(
    key: str, name: str, field_name: str, labels: Sequence[str], question_set: str
) -> dict[str, tuple[str, Callable[[Score], float | None], str]]:
    """One metric per judge label, each a share of every question in the set; plus the share
    without a label (no answer, failed run, or not judged yet), so the rows sum to 100%."""
    metrics: dict[str, tuple[str, Callable[[Score], float | None], str]] = {
        f"{key}_{label}": (
            f"{name}: {label.replace('_', ' ')} (% of set {question_set} questions)",
            _label(field_name, label),
            question_set,
        )
        for label in labels
    }
    metrics[f"{key}_no_label"] = (
        f"{name}: no label — not answered, run failed, or not judged "
        f"(% of set {question_set} questions)",
        _label(field_name, None),
        question_set,
    )
    return metrics


MASKED_LABELS = ("exact", "same_category", "different_category", "not_comparable")
CONSISTENCY_LABELS = ("consistent", "inconsistent")

# Per-question metrics. None = undefined for this question (excluded from that mean).
Metric = Callable[[Score], float | None]
METRICS: dict[str, tuple[str, Metric, str]] = {
    # key: (label, function, question sets)
    "docs": ("Documents returned per question", _ran(lambda s: float(s.n_docs)), "ABC"),
    "answered": (
        "Questions answered from literature",
        _ran(lambda s: float(s.path == "literature")),
        "ABC",
    ),
    **_label_metrics("mc", "Masked correctness", "masked_verdict", MASKED_LABELS, "A"),
    **_label_metrics("fc", "Factual consistency", "consistency", CONSISTENCY_LABELS, "B"),
    **_label_metrics("mc_c", "Masked correctness", "masked_verdict", MASKED_LABELS, "C"),
    **_label_metrics("fc_c", "Factual consistency", "consistency", CONSISTENCY_LABELS, "C"),
    "retrieval_cost": (
        "Retrieval cost per question (search fees, search/rerank LLM; USD)",
        _ran(lambda s: s.retrieval_cost),
        "ABC",
    ),
    "pipeline_cost": (
        "medsim LLM cost per question (Stages A–C, USD)",
        _ran(lambda s: s.pipeline_cost),
        "ABC",
    ),
    "total_cost": ("Total cost per question (USD)", _ran(lambda s: s.total_cost), "ABC"),
    "wall_time": ("Wall time per question (s)", _ran(lambda s: s.wall_time_s), "ABC"),
    "retrieval_time": (
        "Time outside medsim's LLM calls per question (≈ retrieval; s)",
        _ran(lambda s: max(s.wall_time_s - s.llm_time_s, 0.0)),
        "ABC",
    ),
}
LABEL_METRICS = [k for k in METRICS if k.startswith(("mc_", "fc_"))]
PERCENT = {"answered", *LABEL_METRICS}
MONEY = {"retrieval_cost", "pipeline_cost", "total_cost"}


def build_scores(
    ws: Workspace, items: Sequence[Item], configs: Sequence[str], panel: Sequence[str]
) -> list[Score]:
    by_id = {i.item_id: i for i in items}
    masked = panel_judgments(ws.masked_correctness, MaskedCorrectnessJudgment, panel)
    consistency = panel_judgments(ws.consistency, ConsistencyJudgment, panel)
    scores: list[Score] = []
    for config, per_item in latest_runs(ws, configs).items():
        for item in by_id.values():
            run = per_item.get(item.item_id)
            if run is None:  # never run, or failed: counted, without a label
                score = Score(
                    item_id=item.item_id, config=config, question_set=item.question_set,
                    diagnosis=item.diagnosis, category=item.category,
                    characteristic=item.characteristic_of_diagnosis, path=None, n_docs=0,
                    has_answer=False, ran=False,
                )  # fmt: skip
            else:
                score = _score(item, run, masked, consistency, panel)
                score.config = config
            scores.append(score)
    return scores


def _score(
    item: Item,
    run: RunRecord,
    masked: dict[str, dict[str, MaskedCorrectnessJudgment]],
    consistency: dict[str, dict[str, ConsistencyJudgment]],
    panel: Sequence[str],
) -> Score:
    stage_cost: dict[str, float] = {}
    for call in run.llm_calls:
        if call.stage not in RETRIEVAL_STAGES:  # already in run.retrieval_cost_usd
            stage_cost[call.stage] = stage_cost.get(call.stage, 0.0) + (call.cost_usd or 0.0)
    score = Score(
        item_id=item.item_id, config=run.config, question_set=item.question_set,
        diagnosis=item.diagnosis, category=item.category,
        characteristic=item.characteristic_of_diagnosis, path=run.path,
        n_docs=len(run.documents), has_answer=judgeable(run),
        excluded_source_docs=len(run.excluded_source_docs),
        retrieval_cost=run.retrieval_cost_usd, stage_cost=dict(stage_cost),
        wall_time_s=run.wall_time_s,
        llm_time_s=sum(
            c.latency_ms for c in run.llm_calls if c.stage not in RETRIEVAL_STAGES
        ) / 1000,
    )  # fmt: skip
    if not score.has_answer:
        return score
    key = answer_key(item.item_id, run.config, run.output_answer or "")
    metrics = SET_METRICS[item.question_set]
    if "masked_correctness" in metrics:
        judged: dict[str, Any] = masked.get(key, {})
        result = panel_votes(judged, panel)
        score.votes["masked_correctness"] = result.votes
        score.resolution["masked_correctness"] = result.resolution
        score.masked_verdict = result.label
        score.truth_category = panel_votes(judged, panel, "truth_category").label
    if "factual_consistency" in metrics:
        result = panel_votes(consistency.get(key, {}), panel)
        score.votes["factual_consistency"] = result.votes
        score.resolution["factual_consistency"] = result.resolution
        score.consistency = result.label
    return score


def estimate(scores: Sequence[Score], metric: str, *, n_boot: int, seed: int) -> Estimate:
    fn = METRICS[metric][1]
    values = [(s.diagnosis, v) for s in scores if (v := fn(s)) is not None]
    return cluster_bootstrap(values, n_boot=n_boot, seed=seed)


def paired_difference(
    scores: Sequence[Score], metric: str, a: str, b: str, *, n_boot: int, seed: int
) -> Estimate:
    """Mean of (b - a) over questions scored under both configurations."""
    fn = METRICS[metric][1]
    by_config: dict[str, dict[str, Score]] = defaultdict(dict)
    for s in scores:
        by_config[s.config][s.item_id] = s
    values = []
    for item_id, sa in by_config[a].items():
        sb = by_config[b].get(item_id)
        if sb is None:
            continue
        va, vb = fn(sa), fn(sb)
        if va is not None and vb is not None:
            values.append((sa.diagnosis, vb - va))
    return cluster_bootstrap(values, n_boot=n_boot, seed=seed)


def _fmt(metric: str, est: Estimate, *, diff: bool = False) -> str:
    if est.mean is None:
        return "–"
    if metric in MONEY:
        lo = f" [{est.low:+.5f}, {est.high:+.5f}]" if diff and est.low is not None else ""
        return f"{est.mean:+.5f}{lo}" if diff else f"${est.mean:.5f}"
    if metric in PERCENT:
        if diff:
            ci = (
                f" [{est.low * 100:+.0f}, {est.high * 100:+.0f}]"
                if est.low is not None and est.high is not None
                else ""
            )
            return f"{est.mean * 100:+.0f} pts{ci}"
        return est.fmt(pct=True)
    if diff:
        ci = (
            f" [{est.low:+.2f}, {est.high:+.2f}]"
            if est.low is not None and est.high is not None
            else ""
        )
        return f"{est.mean:+.2f}{ci}"
    return est.fmt(digits=2 if metric != "wall_time" else 1)


# --- report sections ----------------------------------------------------------------------------


def comparison_table(
    scores: Sequence[Score],
    configs: Sequence[str],
    question_sets: str,
    metrics: Sequence[str],
    baseline: str,
    *,
    n_boot: int,
    seed: int,
) -> tuple[list[str], dict[str, Any]]:
    subset = [s for s in scores if s.question_set in question_sets]
    others = [c for c in configs if c != baseline]
    header = ["Metric", *configs, *[f"{c} − {baseline}" for c in others]]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    data: dict[str, Any] = {}
    for metric in metrics:
        label, _, sets = METRICS[metric]
        if not set(question_sets) & set(sets):
            continue
        rows = [s for s in subset if s.question_set in sets]
        cells = [label]
        data[metric] = {}
        for config in configs:
            est = estimate(
                [s for s in rows if s.config == config], metric, n_boot=n_boot, seed=seed
            )
            data[metric][config] = asdict(est)
            cells.append(_fmt(metric, est))
        for config in others:
            diff = paired_difference(rows, metric, baseline, config, n_boot=n_boot, seed=seed)
            data[metric][f"{config}-{baseline}"] = asdict(diff)
            cells.append(_fmt(metric, diff, diff=True))
        lines.append("| " + " | ".join(cells) + " |")
    return lines, data


def cost_table(scores: Sequence[Score], configs: Sequence[str]) -> tuple[list[str], dict[str, Any]]:
    lines = [
        "| Method | Questions | Retrieval (search fees + search model) | medsim LLM (Stages A–C) "
        "| Total | Total per question | Median wall time |",
        "|---|---|---|---|---|---|---|",
    ]
    data: dict[str, Any] = {}
    for config in configs:
        rows = [s for s in scores if s.config == config]
        if not rows:
            continue
        retrieval = sum(s.retrieval_cost for s in rows)
        pipeline = sum(s.pipeline_cost for s in rows)
        total = retrieval + pipeline
        wall = statistics.median(s.wall_time_s for s in rows)
        data[config] = {
            "questions": len(rows),
            "retrieval_usd": retrieval,
            "pipeline_llm_usd": pipeline,
            "total_usd": total,
            "per_question_usd": total / len(rows),
            "median_wall_time_s": wall,
        }
        lines.append(
            f"| {config} | {len(rows)} | ${retrieval:.4f} | ${pipeline:.4f} | ${total:.4f} "
            f"| ${total / len(rows):.5f} | {wall:.1f} s |"
        )
    return lines, data


def strata_table(
    scores: Sequence[Score],
    configs: Sequence[str],
    key: Callable[[Score], str],
    metrics: Sequence[str],
) -> list[str]:
    groups = sorted({key(s) for s in scores})
    header = ["Group", "n", *[f"{METRICS[m][0]} — {c}" for m in metrics for c in configs]]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for group in groups:
        rows = [s for s in scores if key(s) == group]
        n = len({s.item_id for s in rows})
        cells = [group, str(n)]
        for metric in metrics:
            fn = METRICS[metric][1]
            for config in configs:
                values = [v for s in rows if s.config == config and (v := fn(s)) is not None]
                mean = _mean(values)
                cells.append("–" if mean is None else (
                    f"{mean * 100:.0f}%" if metric in PERCENT else f"{mean:.2f}"
                ))  # fmt: skip
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def panel_agreement(ws: Workspace, panel: Sequence[str]) -> tuple[list[str], dict[str, Any]]:
    """How the panel reached its labels, and how often each pair of judges agrees."""
    lines = ["| Metric | Answers | Unanimous | Majority | Tie broken by the main judge "
             "| Tie broken by the next judge | Fewer than all votes |",
             "|---|---|---|---|---|---|---|"]  # fmt: skip
    pair_lines: list[str] = []
    data: dict[str, Any] = {"panel": list(panel)}
    by_metric: list[tuple[str, dict[str, dict[str, Any]]]] = [
        ("masked correctness",
         panel_judgments(ws.masked_correctness, MaskedCorrectnessJudgment, panel)),
        ("factual consistency", panel_judgments(ws.consistency, ConsistencyJudgment, panel)),
    ]  # fmt: skip
    for label, judged in by_metric:
        if not judged:
            continue
        results = [panel_votes(j, panel) for j in judged.values()]
        how = Counter(r.resolution for r in results)
        partial = sum(r.n_votes < len(panel) for r in results)
        n = len(results)
        data[label] = {"answers": n, "resolution": dict(how), "fewer_votes": partial, "pairs": {}}
        lines.append(
            f"| {label} | {n} | {how['unanimous'] / n:.0%} | {how['majority'] / n:.0%} "
            f"| {how['tie_break_main_judge'] / n:.0%} | {how['tie_break_next_judge'] / n:.0%} "
            f"| {partial} |"
        )
        for i, a in enumerate(panel):
            for b in panel[i + 1 :]:
                pairs = [(x, y) for r in results
                         if (x := r.votes.get(a)) is not None
                         and (y := r.votes.get(b)) is not None]  # fmt: skip
                if not pairs:
                    continue
                kappa = cohen_kappa([x for x, _ in pairs], [y for _, y in pairs])
                agree = sum(x == y for x, y in pairs)
                data[label]["pairs"][f"{a} | {b}"] = {"n": len(pairs), "agree": agree,
                                                      "kappa": kappa}  # fmt: skip
                pair_lines.append(
                    f"- **{label}, `{a}` vs `{b}`:** {agree}/{len(pairs)} identical labels, "
                    f"Cohen's κ = {kappa:.2f}."
                )
    if len(lines) == 2:
        return [], data
    return [*lines, "", *pair_lines], data


def validation_section(ws: Workspace, panel: Sequence[str]) -> tuple[list[str], dict[str, Any]]:
    lines: list[str] = []
    data: dict[str, Any] = {}
    controls = [c for c in read_models(ws.controls, ControlResult)
                if c.judges == list(panel) and c.rubric == RUBRIC]  # fmt: skip
    if controls:
        lines += ["| Control answer | Expected voted label | Passed |", "|---|---|---|"]
        by_kind: dict[str, list[ControlResult]] = defaultdict(list)
        for c in controls:
            by_kind[c.control].append(c)
        for kind, results in sorted(by_kind.items()):
            scored = [c for c in results if c.passed is not None]
            passed = sum(bool(c.passed) for c in scored)
            data[f"control_{kind}"] = {"passed": passed, "n": len(scored)}
            lines.append(f"| {kind} | {results[0].expected} | {passed}/{len(scored)} |")
        lines.append("")
    flips = [
        f
        for f in read_models(ws.flips, FlipResult)
        if f.judges == list(panel) and f.rubric == RUBRIC and f.passed is not None
    ]
    if flips:
        passed = sum(bool(f.passed) for f in flips)
        data["flipped_truth"] = {"changed": passed, "n": len(flips)}
        lines.append(
            f"- **Flipped true value:** after moving the true value far away, the voted label "
            f'of {passed} of {len(flips)} "exact" answers changed. An unchanged label is not '
            f"always an error: when an answer states a wide range, the moved value can still be "
            f"inside it (see validate/flips.jsonl)."
        )
    human = read_human_labels(ws)
    if human:
        masked = panel_judgments(ws.masked_correctness, MaskedCorrectnessJudgment, panel)
        consistency = panel_judgments(ws.consistency, ConsistencyJudgment, panel)
        for label, column, judged in (
            ("masked correctness", "human_masked_verdict", masked),
            ("factual consistency", "human_consistency", consistency),
        ):
            rows = [
                (h[column].strip(), voted)
                for h in human
                if h[column].strip()
                and (voted := panel_votes(judged.get(h["answer_key"], {}), panel).label) is not None
            ]
            if rows:
                kappa = cohen_kappa([a for a, _ in rows], [b for _, b in rows])
                data[f"human_{label.replace(' ', '_')}"] = {"n": len(rows), "kappa": kappa}
                lines.append(
                    f"- **Human labels vs the voted label, {label} ({len(rows)} answers):** "
                    f"κ = {kappa:.2f}."
                )
    return lines, data


def spend_section(ws: Workspace, scores: Sequence[Score]) -> tuple[list[str], dict[str, Any]]:
    """Every benchmark LLM call's cost, from the usage.cost OpenRouter reported for it."""
    sources: list[tuple[str, Any, Any]] = [
        ("extract (case facts)", ws.facts, CaseFacts),
        ("redact + Stage A checks (accepted)", ws.items, Item),
        ("redact + Stage A checks (rejected)", ws.rejected, RejectedItem),
    ]
    rows: list[tuple[str, float]] = [
        (label, sum(calls_cost(r.llm_calls) for r in read_models(path, model)))
        for label, path, model in sources
    ]
    judge_files: list[tuple[str, Any, Any]] = [
        ("masked correctness", ws.masked_correctness, MaskedCorrectnessJudgment),
        ("factual consistency", ws.consistency, ConsistencyJudgment),
    ]
    for metric, path, cls in judge_files:
        by_model: dict[str, float] = defaultdict(float)
        for r in read_models(path, cls):
            by_model[r.judge_model] += calls_cost(r.llm_calls)
        rows += [(f"judge: {metric} ({model})", cost) for model, cost in by_model.items()]
    rows += [
        ("validation: controls (panel)",
         sum(calls_cost(r.llm_calls) for r in read_models(ws.controls, ControlResult))),
        ("validation: flipped truth (panel)",
         sum(calls_cost(r.llm_calls) for r in read_models(ws.flips, FlipResult))),
    ]  # fmt: skip
    rows.insert(3, ("run (all methods; search fees included)", sum(s.total_cost for s in scores)))
    total = sum(v for _, v in rows)
    lines = ["| Step | Cost (USD, OpenRouter usage.cost) |", "|---|---|"]
    lines += [f"| {label} | ${value:.4f} |" for label, value in rows]
    lines.append(f"| **total** | **${total:.4f}** |")
    data: dict[str, Any] = {"by_step": dict(rows), "total": total}
    steps = load_manifest(ws).get("steps", [])
    measured = [s for s in steps if "key_usage_before" in s and "key_usage_after" in s]
    if measured:
        delta = sum(s["key_usage_after"] - s["key_usage_before"] for s in measured)
        data["key_usage_delta"] = delta
        lines += [
            "",
            f"Cross-check: the OpenRouter key's usage counter, read right after each of the "
            f"{len(measured)} benchmark commands, rose by ${delta:.4f}. The counter lags behind "
            f"requests, so this undercounts; per-call usage.cost above is the accounting source.",
        ]
    return lines, data


def diagnostics(
    scores: Sequence[Score], configs: Sequence[str], ws: Workspace, panel: Sequence[str]
) -> list[str]:
    lines = []
    for config in configs:
        rows = [s for s in scores if s.config == config]
        paths = Counter(s.path if s.ran else "not run" for s in rows)
        excluded = sum(1 for s in rows if s.excluded_source_docs)
        verdicts = {"masked_correctness": "masked_verdict", "factual_consistency": "consistency"}
        unjudged = sum(
            1
            for s in rows
            if s.has_answer
            and any(getattr(s, verdicts[m]) is None for m in SET_METRICS[s.question_set])
        )
        short = sum(
            1
            for s in rows
            if any(sum(v is not None for v in by.values()) < len(panel) for by in s.votes.values())
        )
        lines.append(
            f"- **{config}:** answer paths {dict(paths)}; source article removed for {excluded} "
            f"question(s); {unjudged} answer(s) without any judge's verdict; "
            f"{short} answer(s) voted on by fewer than all {len(panel)} judges."
        )
    voted_a = [s for s in scores if s.question_set == "A" and s.masked_verdict is not None]
    not_comparable = sum(s.masked_verdict == "not_comparable" for s in voted_a)
    lines.append(
        f'- **Masked correctness:** {not_comparable} of {len(voted_a)} voted labels were "not '
        f'comparable" (reported as their own label).'
    )
    errors = sum(
        1
        for path, cls in ((ws.masked_correctness, MaskedCorrectnessJudgment),
                          (ws.consistency, ConsistencyJudgment))
        for j in read_models(path, cls)
        if j.status == "error"
    )  # fmt: skip
    lines.append(
        f"- **Judge errors (all attempts, all judges):** {errors} judgment(s) failed; rerun the "
        f"judge step to retry them."
    )
    return lines


def funnel(ws: Workspace, items: Sequence[Item]) -> list[str]:
    facts = [f for f in read_models(ws.facts, CaseFacts) if f.status == "ok"]
    n_facts = sum(len(f.facts) for f in facts)
    eligible = sum(sum(x.eligible for x in f.facts) for f in facts)
    rejected = Counter(
        r.reason for r in read_models(ws.rejected, RejectedItem) if r.question_set == "A"
    )
    rejected_b = Counter(
        r.reason for r in read_models(ws.rejected, RejectedItem) if r.question_set == "B"
    )
    a = sum(i.question_set == "A" for i in items)
    b = sum(i.question_set == "B" for i in items)
    c = sum(i.question_set == "C" for i in items)
    rejected_c = Counter(
        r.reason for r in read_models(ws.rejected, RejectedItem) if r.question_set == "C"
    )
    set_c = [
        f"- Set C (information the case states): {c} questions accepted; rejected "
        f"{sum(rejected_c.values())} "
        f"({', '.join(f'{k}: {v}' for k, v in rejected_c.most_common()) or 'none'})."
    ]
    return [
        f"- Cases extracted: {len(facts)}; measured values found: {n_facts}; eligible as hidden "
        f"values: {eligible}.",
        f"- Set A (hidden value): {a} questions accepted; rejected {sum(rejected.values())} "
        f"({', '.join(f'{k}: {v}' for k, v in rejected.most_common()) or 'none'}).",
        f"- Set B (value never stated): {b} questions accepted; rejected "
        f"{sum(rejected_b.values())} "
        f"({', '.join(f'{k}: {v}' for k, v in rejected_b.most_common()) or 'none'}).",
        *(set_c if c or rejected_c else []),
    ]


COST_TIME = {"retrieval_cost", "pipeline_cost", "total_cost", "wall_time", "retrieval_time"}
MAIN_METRICS = ["docs", "answered", *LABEL_METRICS, "retrieval_cost", "pipeline_cost",
                "total_cost", "wall_time", "retrieval_time"]  # fmt: skip


def build_report(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[str],
    *,
    judge_models: Sequence[str],
    baseline: str,
    n_boot: int = 2000,
    seed: int = 11,
) -> tuple[str, dict[str, Any]]:
    panel = list(judge_models)
    all_scores = build_scores(ws, items, configs, panel)
    configs = [c for c in configs if any(s.config == c and s.ran for s in all_scores)]
    if baseline not in configs:
        baseline = configs[0]
    scores = [s for s in all_scores if s.config in configs]
    manifest = load_manifest(ws)
    data: dict[str, Any] = {"configs": configs, "baseline": baseline, "judge_panel": panel}
    md: list[str] = ["# Retrieval benchmark report", ""]
    md += [
        f"- Workspace: `{ws.root}`",
        f"- Judge panel: {', '.join(f'`{m}`' for m in panel)}. Each answer's label is the "
        f"panel's majority vote; with no majority, the first (main) judge's label decides.",
    ]
    pipeline = (manifest.get("latest", {}).get("run") or {}).get("pipeline_models")
    if pipeline:
        md.append(f"- medsim models: `{', '.join(pipeline)}`")
    for config in configs:
        desc = CONFIGS[config].description if config in CONFIGS else ""
        md.append(f"- `{config}`: {desc}")
    md += ["", "## Question sets", "", *funnel(ws, items)]
    not_run = {c: sum(1 for s in scores if s.config == c and not s.ran) for c in configs}
    md.append(
        "- Every question is scored under every method: each label's percentage is out of all "
        "questions in its set. Questions without a successful run (counted as no label): "
        + ", ".join(f"{c}: {n}" for c, n in not_run.items())
        + "."
    )
    md.append("")
    data["not_run"] = not_run

    sets = "".join(q for q in "ABC" if any(s.question_set == q for s in scores))
    md += [f"## All questions (sets {', '.join(sets)})", ""]
    lines, data["all"] = comparison_table(
        scores, configs, sets, MAIN_METRICS, baseline, n_boot=n_boot, seed=seed
    )
    md += [*lines, ""]
    for question_set, title in (
        ("A", "Set A only (hidden value; masked correctness)"),
        ("B", "Set B only (value never stated; factual consistency)"),
        ("C", "Set C only (information the case states; both metrics)"),
    ):
        if question_set not in sets:
            continue
        lines, data[f"set_{question_set}"] = comparison_table(
            scores,
            configs,
            question_set,
            [m for m in MAIN_METRICS if m not in COST_TIME],
            baseline,
            n_boot=n_boot,
            seed=seed,
        )
        md += [f"## {title}", "", *lines, ""]

    md += [
        "## Cost",
        "",
        "All questions that ran.",
        "",
    ]
    lines, data["cost"] = cost_table([s for s in scores if s.ran], configs)
    md += [*lines, ""]

    md += ["## By subgroup (set A)", ""]
    set_a = [s for s in scores if s.question_set == "A"]
    for title, key in (
        ("Variable category", lambda s: s.category),
        ("True value (judge's category)", lambda s: s.truth_category or "unknown"),
        (
            "Variable typical of the diagnosis",
            lambda s: {True: "yes", False: "no", None: "?"}[s.characteristic],
        ),
    ):
        strata = strata_table(set_a, configs, key, ["mc_exact", "mc_different_category"])
        md += [f"### {title}", "", *strata, ""]

    md += ["## Diagnostics", "", *diagnostics(scores, configs, ws, panel), ""]
    lines, data["panel_agreement"] = panel_agreement(ws, panel)
    if lines:
        md += ["## Judge panel agreement", "", *lines, ""]
    lines, data["validation"] = validation_section(ws, panel)
    if lines:
        md += ["## Judge validation", "", *lines, ""]
    lines, data["spend"] = spend_section(ws, [s for s in all_scores if s.ran])
    md += ["## Benchmark spend", "", *lines, ""]
    data["scores"] = [asdict(s) for s in all_scores]
    return "\n".join(md), data


def write_report(ws: Workspace, markdown: str, data: dict[str, Any]) -> None:
    ws.report_md.write_text(markdown + "\n", encoding="utf-8")
    ws.report_json.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
