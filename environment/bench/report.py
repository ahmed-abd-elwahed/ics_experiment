"""Step 6: turn judgments into per-question scores, compare configurations, write the report."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from bench.judge import answer_key, doc_key, latest_runs, ok_judgments
from bench.run import CONFIGS, RETRIEVAL_STAGES
from bench.schemas import (
    AnswerJudgment,
    CaseFacts,
    ControlResult,
    FlipResult,
    Item,
    Pass1Judgment,
    Pass2Judgment,
    RejectedItem,
    RunRecord,
    calls_cost,
)
from bench.stats import Estimate, cluster_bootstrap, cohen_kappa
from bench.validate import read_human_labels
from bench.workspace import Workspace, load_manifest, read_models


@dataclass
class Score:
    """One question under one configuration."""

    item_id: str
    config: str
    question_set: str
    diagnosis: str
    category: str
    characteristic: bool | None
    path: str | None
    n_docs: int
    n_judged: int
    relevance: list[int] = field(default_factory=list)
    usefulness: list[int] = field(default_factory=list)
    correctness: list[int] = field(default_factory=list)  # comparable verdicts, docs with U >= 1
    sources: list[str] = field(default_factory=list)
    truth_category: str | None = None
    answer_verdict: str | None = None
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


# Per-question metrics. None = undefined for this question (excluded from that mean).
Metric = Callable[[Score], float | None]
METRICS: dict[str, tuple[str, Metric, str]] = {
    # key: (label, function, question sets)
    "docs": ("Documents returned per question", lambda s: float(s.n_docs), "AB"),
    "mean_relevance": ("Mean relevance grade (0–3)", lambda s: _mean(s.relevance), "AB"),
    "p_relevant": (
        "Relevant documents (grade ≥ 2), share",
        lambda s: _mean([r >= 2 for r in s.relevance]),
        "AB",
    ),
    "u_hit": (
        "Questions with ≥ 1 useful document (usefulness 2)",
        lambda s: float(any(u == 2 for u in s.usefulness)),
        "AB",
    ),
    "u_precision": (
        "Useful documents (usefulness 2), share",
        lambda s: _mean([u == 2 for u in s.usefulness]),
        "AB",
    ),
    "c_hit": (
        "Questions with ≥ 1 document containing the true value (correctness 2)",
        lambda s: float(any(c == 2 for c in s.correctness)),
        "A",
    ),
    "c_precision": (
        "Number-giving documents pointing the right way (correctness ≥ 1), share",
        lambda s: _mean([c >= 1 for c in s.correctness]),
        "A",
    ),
    "majority_correct": (
        "Questions where most number-giving documents point the right way",
        lambda s: float(bool(s.correctness) and _mean([c >= 1 for c in s.correctness]) > 0.5),  # type: ignore[operator]
        "A",
    ),
    "answered": (
        "Questions answered from literature",
        lambda s: float(s.path == "literature"),
        "AB",
    ),
    "answer_close": (
        "Final answer close to the true value",
        lambda s: float(s.answer_verdict == "close"),
        "A",
    ),
    "answer_category": (
        "Final answer in the true value's category (low/normal/high)",
        lambda s: float(s.answer_verdict in ("close", "same_category")),
        "A",
    ),
    "retrieval_cost": (
        "Retrieval cost per question (search fees, search/rerank LLM; USD)",
        lambda s: s.retrieval_cost,
        "AB",
    ),
    "pipeline_cost": (
        "medsim LLM cost per question (Stages A–C, USD)",
        lambda s: s.pipeline_cost,
        "AB",
    ),
    "total_cost": ("Total cost per question (USD)", lambda s: s.total_cost, "AB"),
    "wall_time": ("Wall time per question (s)", lambda s: s.wall_time_s, "AB"),
    "retrieval_time": (
        "Time outside medsim's LLM calls per question (≈ retrieval; s)",
        lambda s: max(s.wall_time_s - s.llm_time_s, 0.0),
        "AB",
    ),
}
PERCENT = {"p_relevant", "u_hit", "u_precision", "c_hit", "c_precision", "majority_correct",
           "answered", "answer_close", "answer_category"}  # fmt: skip
MONEY = {"retrieval_cost", "pipeline_cost", "total_cost"}


# Paths on which medsim answered without retrieving anything.
NO_RETRIEVAL = {"case_study", "off_topic", "withheld", "ledger_hit", "empty_query",
                "query_builder_declined"}  # fmt: skip


def comparable(
    scores: Sequence[Score], configs: Sequence[str]
) -> tuple[list[Score], dict[str, dict[str, str]]]:
    """Scores for questions on which every configuration ran and retrieved.

    Stage A is not perfectly deterministic: now and then it answers a set A question from the
    redacted case (e.g. from a kept qualitative mention), so no retrieval runs. Comparing such a
    question would penalise one method by chance, so it is excluded and listed instead.
    """
    by_item: dict[str, dict[str, Score]] = defaultdict(dict)
    for s in scores:
        by_item[s.item_id][s.config] = s
    kept: list[Score] = []
    excluded: dict[str, dict[str, str]] = {}
    for item_id, per_config in by_item.items():
        paths = {c: (per_config[c].path or "?") if c in per_config else "missing" for c in configs}
        if any(p == "missing" or p in NO_RETRIEVAL for p in paths.values()):
            excluded[item_id] = paths
        else:
            kept.extend(per_config[c] for c in configs)
    return kept, excluded


def build_scores(
    ws: Workspace, items: Sequence[Item], configs: Sequence[str], judge_model: str
) -> list[Score]:
    by_id = {i.item_id: i for i in items}
    pass1 = ok_judgments(ws.pass1, Pass1Judgment, judge_model)
    pass2 = ok_judgments(ws.pass2, Pass2Judgment, judge_model)
    answers = ok_judgments(ws.answers, AnswerJudgment, judge_model)
    scores: list[Score] = []
    for config, per_item in latest_runs(ws, configs).items():
        for item_id, run in per_item.items():
            item = by_id.get(item_id)
            if item is None:
                continue
            score = _score(item, run, pass1, pass2, answers)
            score.config = config
            scores.append(score)
    return scores


def _score(
    item: Item,
    run: RunRecord,
    pass1: dict[str, Pass1Judgment],
    pass2: dict[str, Pass2Judgment],
    answers: dict[str, AnswerJudgment],
) -> Score:
    stage_cost: dict[str, float] = {}
    for call in run.llm_calls:
        if call.stage not in RETRIEVAL_STAGES:  # already in run.retrieval_cost_usd
            stage_cost[call.stage] = stage_cost.get(call.stage, 0.0) + (call.cost_usd or 0.0)
    score = Score(
        item_id=item.item_id, config=run.config, question_set=item.question_set,
        diagnosis=item.diagnosis, category=item.category,
        characteristic=item.characteristic_of_diagnosis, path=run.path,
        n_docs=len(run.documents), n_judged=0,
        excluded_source_docs=len(run.excluded_source_docs),
        retrieval_cost=run.retrieval_cost_usd, stage_cost=dict(stage_cost),
        wall_time_s=run.wall_time_s,
        llm_time_s=sum(
            c.latency_ms for c in run.llm_calls if c.stage not in RETRIEVAL_STAGES
        ) / 1000,
    )  # fmt: skip
    truth_categories: list[str] = []
    for doc in run.documents:
        key = doc_key(item.item_id, doc.doc_id, doc.text)
        judged = pass1.get(key)
        if judged is None or judged.relevance is None or judged.usefulness is None:
            continue
        score.n_judged += 1
        score.relevance.append(judged.relevance)
        score.usefulness.append(judged.usefulness)
        score.sources.append(doc.source)
        second = pass2.get(key)
        if item.truth is not None and judged.usefulness >= 1 and second and second.output:
            truth_categories.append(second.output.truth_category)
            if second.correctness is not None:
                score.correctness.append(second.correctness)
    if item.truth is not None and run.answer_source == "literature":
        judged_answer = answers.get(answer_key(item.item_id, run.config, run.output_answer or ""))
        if judged_answer and judged_answer.output:
            score.answer_verdict = judged_answer.output.verdict
            truth_categories.append(judged_answer.output.truth_category)
    if truth_categories:
        score.truth_category = Counter(truth_categories).most_common(1)[0][0]
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


def source_table(scores: Sequence[Score]) -> list[str]:
    """Document-level grades by the source that returned the document."""
    rel: dict[str, list[int]] = defaultdict(list)
    use: dict[str, list[int]] = defaultdict(list)
    for s in scores:
        for source, grade_r, grade_u in zip(s.sources, s.relevance, s.usefulness, strict=True):
            rel[source].append(grade_r)
            use[source].append(grade_u)
    lines = ["| Source | Documents judged | Mean relevance | Relevant (≥ 2) | Useful (= 2) |",
             "|---|---|---|---|---|"]  # fmt: skip
    for source in sorted(rel):
        r, u = rel[source], use[source]
        relevant = sum(x >= 2 for x in r) / len(r) * 100
        useful = sum(x == 2 for x in u) / len(u) * 100
        lines.append(
            f"| {source} | {len(r)} | {sum(r) / len(r):.2f} | {relevant:.0f}% | {useful:.0f}% |"
        )
    return lines


def validation_section(
    ws: Workspace, judge_model: str, second_model: str | None
) -> tuple[list[str], dict[str, Any]]:
    lines: list[str] = []
    data: dict[str, Any] = {}
    controls = [c for c in read_models(ws.controls, ControlResult) if c.judge_model == judge_model]
    if controls:
        lines += ["| Control document | Expected | Passed |", "|---|---|---|"]
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
        if f.judge_model == judge_model and f.passed is not None
    ]
    if flips:
        passed = sum(bool(f.passed) for f in flips)
        data["flipped_truth"] = {"changed": passed, "n": len(flips)}
        lines.append(
            f"- **Flipped true value:** after moving the true value far away, {passed} of "
            f'{len(flips)} "within" verdicts changed. An unchanged verdict is not always an '
            f"error: when a document reports a wide range, the moved value can still be inside it "
            f"(see validate/flips.jsonl)."
        )
    if second_model:
        primary1 = ok_judgments(ws.pass1, Pass1Judgment, judge_model)
        second1 = ok_judgments(ws.second_pass1, Pass1Judgment, second_model)
        shared = [k for k in second1 if k in primary1]
        if shared:
            rel = cohen_kappa(
                [primary1[k].relevance or 0 for k in shared],
                [second1[k].relevance or 0 for k in shared],
                weights="quadratic",
            )
            use = cohen_kappa(
                [primary1[k].usefulness or 0 for k in shared],
                [second1[k].usefulness or 0 for k in shared],
                weights="quadratic",
            )
            data["second_judge_pass1"] = {
                "n": len(shared),
                "kappa_relevance": rel,
                "kappa_usefulness": use,
            }
            lines.append(
                f"- **Second judge ({second_model}), {len(shared)} documents:** quadratic-weighted "
                f"κ = {rel:.2f} for relevance, {use:.2f} for usefulness."
            )
        primary2 = ok_judgments(ws.pass2, Pass2Judgment, judge_model)
        second2 = ok_judgments(ws.second_pass2, Pass2Judgment, second_model)
        pairs = [
            (p.output.verdict, q.output.verdict)
            for k, q in second2.items()
            if (p := primary2.get(k)) is not None and p.output and q.output
        ]
        if pairs:
            shared2 = pairs
            kappa = cohen_kappa([a for a, _ in pairs], [b for _, b in pairs])
            agree = sum(a == b for a, b in pairs)
            data["second_judge_pass2"] = {
                "n": len(shared2),
                "kappa_verdict": kappa,
                "agreement": agree,
            }
            lines.append(
                f"- **Second judge, correctness verdicts ({len(shared2)} documents):** "
                f"{agree}/{len(shared2)} identical, Cohen's κ = {kappa:.2f}."
            )
    human = read_human_labels(ws)
    if human:
        primary1 = ok_judgments(ws.pass1, Pass1Judgment, judge_model)
        rows = [h for h in human if h["doc_key"] in primary1]
        kappa = cohen_kappa(
            [int(h["human_relevance_0_3"]) for h in rows],
            [primary1[h["doc_key"]].relevance or 0 for h in rows],
            weights="quadratic",
        )
        data["human_relevance"] = {"n": len(rows), "kappa": kappa}
        lines.append(f"- **Human labels ({len(rows)} documents):** relevance κ = {kappa:.2f}.")
    return lines, data


def spend_section(ws: Workspace, scores: Sequence[Score]) -> tuple[list[str], dict[str, Any]]:
    """Every benchmark LLM call's cost, from the usage.cost OpenRouter reported for it."""
    sources: list[tuple[str, Any, Any]] = [
        ("extract (case facts)", ws.facts, CaseFacts),
        ("redact + Stage A checks (accepted)", ws.items, Item),
        ("redact + Stage A checks (rejected)", ws.rejected, RejectedItem),
        ("judge pass 1", ws.pass1, Pass1Judgment),
        ("judge pass 2", ws.pass2, Pass2Judgment),
        ("judge answer check", ws.answers, AnswerJudgment),
        ("validation: controls", ws.controls, ControlResult),
        ("validation: flipped truth", ws.flips, FlipResult),
        ("validation: second judge, pass 1", ws.second_pass1, Pass1Judgment),
        ("validation: second judge, pass 2", ws.second_pass2, Pass2Judgment),
    ]
    rows = [(label, sum(calls_cost(r.llm_calls) for r in read_models(path, model)))
            for label, path, model in sources]  # fmt: skip
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
    scores: Sequence[Score], configs: Sequence[str], ws: Workspace, judge_model: str
) -> list[str]:
    lines = []
    for config in configs:
        rows = [s for s in scores if s.config == config]
        paths = Counter(s.path for s in rows)
        excluded = sum(1 for s in rows if s.excluded_source_docs)
        unjudged = sum(s.n_docs - s.n_judged for s in rows)
        lines.append(
            f"- **{config}:** answer paths {dict(paths)}; source article removed for {excluded} "
            f"question(s); {unjudged} document(s) without a judgment."
        )
    pass1 = [
        j
        for j in read_models(ws.pass1, Pass1Judgment)
        if j.judge_model == judge_model and j.status == "ok"
    ]
    quote_fail = sum(1 for j in pass1 if j.quote_ok is False)
    lines.append(
        f"- **Quote check:** {quote_fail} of {len(pass1)} pass-1 judgments quoted text that is not "
        f"in the document (usefulness forced to 0)."
    )
    pass2 = [
        j
        for j in read_models(ws.pass2, Pass2Judgment)
        if j.judge_model == judge_model and j.status == "ok" and j.truth_override is None
    ]
    not_comparable = sum(1 for j in pass2 if j.output and j.output.verdict == "not_comparable")
    lines.append(
        f'- **Pass 2:** {not_comparable} of {len(pass2)} verdicts were "not comparable" '
        f"(excluded from correctness)."
    )
    errors = sum(1 for j in read_models(ws.pass1, Pass1Judgment) if j.status == "error")
    lines.append(f"- **Judge errors (all attempts):** {errors} pass-1 call(s) failed.")
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
    return [
        f"- Cases extracted: {len(facts)}; measured values found: {n_facts}; eligible as hidden "
        f"values: {eligible}.",
        f"- Set A (hidden value): {a} questions accepted; rejected {sum(rejected.values())} "
        f"({', '.join(f'{k}: {v}' for k, v in rejected.most_common()) or 'none'}).",
        f"- Set B (value never stated): {b} questions accepted; rejected "
        f"{sum(rejected_b.values())} "
        f"({', '.join(f'{k}: {v}' for k, v in rejected_b.most_common()) or 'none'}).",
    ]


COST_TIME = {"retrieval_cost", "pipeline_cost", "total_cost", "wall_time", "retrieval_time"}
MAIN_METRICS = ["docs", "mean_relevance", "p_relevant", "u_hit", "u_precision", "c_hit",
                "c_precision", "majority_correct", "answered", "answer_close", "answer_category",
                "retrieval_cost", "pipeline_cost", "total_cost", "wall_time",
                "retrieval_time"]  # fmt: skip


def build_report(
    ws: Workspace,
    items: Sequence[Item],
    configs: Sequence[str],
    *,
    judge_model: str,
    second_judge_model: str | None,
    baseline: str,
    n_boot: int = 2000,
    seed: int = 11,
) -> tuple[str, dict[str, Any]]:
    all_scores = build_scores(ws, items, configs, judge_model)
    configs = [c for c in configs if any(s.config == c for s in all_scores)]
    if baseline not in configs:
        baseline = configs[0]
    scores, excluded = comparable(all_scores, configs)
    manifest = load_manifest(ws)
    data: dict[str, Any] = {"configs": configs, "baseline": baseline, "judge_model": judge_model}
    md: list[str] = ["# Retrieval benchmark report", ""]
    md += [f"- Workspace: `{ws.root}`", f"- Judge: `{judge_model}`"]
    pipeline = (manifest.get("latest", {}).get("run") or {}).get("pipeline_models")
    if pipeline:
        md.append(f"- medsim models: `{', '.join(pipeline)}`")
    for config in configs:
        desc = CONFIGS[config].description if config in CONFIGS else ""
        md.append(f"- `{config}`: {desc}")
    md += ["", "## Question sets", "", *funnel(ws, items)]
    compared = len({s.item_id for s in scores})
    listed = "; ".join(
        f"`{k}` ({', '.join(f'{c}: {p}' for c, p in v.items())})"
        for k, v in sorted(excluded.items())
    )
    md.append(
        f"- Compared: {compared} questions on which every method ran retrieval; excluded "
        f"{len(excluded)}: {listed or 'none'}."
    )
    md.append("")
    data["excluded"] = excluded

    md += ["## All questions (sets A and B)", ""]
    lines, data["all"] = comparison_table(
        scores, configs, "AB", MAIN_METRICS, baseline, n_boot=n_boot, seed=seed
    )
    md += [*lines, ""]
    for question_set, title in (("A", "Set A only (hidden value; correctness defined)"),
                                ("B", "Set B only (value never stated)")):  # fmt: skip
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
        "All runs, including the excluded questions (their calls were paid for).",
        "",
    ]
    lines, data["cost"] = cost_table(all_scores, configs)
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
        md += [f"### {title}", "", *strata_table(set_a, configs, key, ["u_hit", "c_hit"]), ""]
    md += ["### Documents by source", "", *source_table(scores), ""]

    md += ["## Diagnostics", "", *diagnostics(scores, configs, ws, judge_model), ""]
    lines, data["validation"] = validation_section(ws, judge_model, second_judge_model)
    if lines:
        md += ["## Judge validation", "", *lines, ""]
    lines, data["spend"] = spend_section(ws, all_scores)
    md += ["## Benchmark spend", "", *lines, ""]
    data["scores"] = [asdict(s) for s in all_scores]
    return "\n".join(md), data


def write_report(ws: Workspace, markdown: str, data: dict[str, Any]) -> None:
    ws.report_md.write_text(markdown + "\n", encoding="utf-8")
    ws.report_json.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
