"""Score the five answer metrics for every run, configuration and judge panel; no API calls.

Usage:
  python environment/results/scripts/make_answer_metrics.py test --run 2 --panel MODEL
  python environment/results/scripts/make_answer_metrics.py full

``test`` prints the sensitivity of each metric on one run (paired cluster bootstrap over
diagnoses). ``full`` writes environment/results/answer_metrics/answer_metrics.json and .md: each
metric as mean ± SD over the runs, for the three-judge panel and for the panel with the Jev
decision model added, and each metric's sensitivity across runs.

Per question, each metric is one number: 1 or 0 for a label's share, or the capped |z| for the
zlog z-score. A question medsim did not answer counts as 0 (as 3 for the zlog z-score), so every
share is over the full question set. A run counts for a metric and configuration only when
every judge of the panel has judged it (at least 98% of its answers).
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from bench.answer_metrics import (
    JEV_MODEL,
    NO_DOCUMENT_CONFIGS,
    SHARED,
    load_references,
    metric_path,
    ok_metric_judgments,
    scorable,
    value_score,
)
from bench.config import BenchSettings
from bench.judge import answer_key, latest_runs, vote
from bench.report import build_scores
from bench.schemas import Item
from bench.workspace import Workspace, read_models
from bench.zlog import SATISFACTORY, SCORE_CAP

RESULTS = Path(__file__).resolve().parents[1]
REPO = RESULTS.parents[1]

# (configuration, row name, workspace kind)
ORDER = [
    ("gemini_knowledge", "Gemini 3 Flash knowledge, no search", "ab"),
    ("current", "Europe PMC + LitSense, without changes 1–4", "ab"),
    ("improved_1to4", "Europe PMC + LitSense, with changes 1–4", "ab"),
    ("openrouter_exa_instant", "OpenRouter search: Exa instant", "ab"),
    ("openrouter_parallel_basic", "OpenRouter search: Parallel basic", "ab"),
    ("openrouter_perplexity", "OpenRouter search: Perplexity", "ab"),
    ("openrouter_google", "Native Google search (one run)", "ab"),
    ("openrouter_openai", "Native OpenAI search (one run)", "ab"),
    ("case_information", "Case study only, no retrieval (set C)", "c"),
]
SINGLE_RUN = ("openrouter_google", "openrouter_openai")
REPEATED = [c for c, _, k in ORDER if k == "ab" and c not in SINGLE_RUN]
# metric key -> (title, the judged metric it comes from, higher is better, old or new)
METRICS: dict[str, tuple[str, str, bool, str]] = {
    "mc_same": (
        "Masked correctness: same category (incl. exact), %", "masked_correctness", True, "old",
    ),
    "mc_exact": ("Masked correctness: exact, %", "masked_correctness", True, "old"),
    "fc_consistent": ("Factual consistency: consistent, %", "factual_consistency", True, "old"),
    "zlog": ("Zlog z-score: mean |z| (capped at 3)", "zlog_value", False, "new"),
    "zlog_sat": ("Zlog z-score: satisfactory (|z| ≤ 2), %", "zlog_value", True, "new"),
    "faith": ("Faithfulness: supported, %", "faithfulness", True, "new"),
    "align_aligned": ("Case alignment: aligned, %", "case_alignment", True, "new"),
    "align_contra": ("Case alignment: contradicted, %", "case_alignment", False, "new"),
}  # fmt: skip
# The other version of the two revised metrics, kept for the comparison in the test stage.
VARIANTS: dict[str, tuple[str, str, bool, str]] = {
    "zlog_v1": ("Zlog z-score, first version: mean |z|", "zlog_value", False, "new"),
    "zlog_v1_sat": ("Zlog z-score, first version: satisfactory, %", "zlog_value", True, "new"),
    "align_v1_aligned": (
        "Case alignment, first version: aligned, %", "case_alignment_v1", True, "new",
    ),
    "align_v1_contra": (
        "Case alignment, first version: contradicted, %", "case_alignment_v1", False, "new",
    ),
}  # fmt: skip
# Further readings of a judged metric, scored but not in the main table.
EXTRA: dict[str, tuple[str, str, bool, str]] = {
    "align_ok": ("Case alignment: aligned or neutral, %", "case_alignment", True, "new"),
    "align_neutral": ("Case alignment: neutral, %", "case_alignment", True, "new"),
}
ALL = METRICS | VARIANTS | EXTRA
PERCENT = {k for k in ALL if k not in ("zlog", "zlog_v1")}
# The versions kept after the test stage (see bench/README.md): the revised zlog scale and the
# revised case alignment rubric.
ZLOG_SCALED = True
ALIGNMENT_RUBRIC = "m2"
COMPLETE = 0.98  # share of a configuration's answers each judge must have judged

Values = dict[str, dict[str, dict[str, float]]]  # metric -> config -> item id -> value
Coverage = dict[tuple[str, str], float]  # (judged metric, config) -> lowest judge's share


def workspace_values(
    ws: Workspace, kind: str, panel: list[str], references: dict[str, Any]
) -> tuple[Values, dict[str, str], Coverage]:
    """Per-question values of every metric in one workspace, the questions' diagnoses, and how
    much of each configuration's answers every panel judge has judged."""
    items = read_models(ws.items, Item)
    by_id = {i.item_id: i for i in items}
    configs = [c for c, _, k in ORDER if k == kind and ws.run_file(c).exists()]
    scores = build_scores(ws, items, configs, panel)
    runs = latest_runs(ws, configs)
    chat = [m for m in panel if m != JEV_MODEL]
    other_rubric = "m1" if ALIGNMENT_RUBRIC == "m2" else "m2"
    rubrics = {"zlog_value": "m1", "faithfulness": "m1", "case_alignment": ALIGNMENT_RUBRIC,
               "case_alignment_v1": other_rubric}  # fmt: skip
    judged = {
        metric: {
            m: ok_metric_judgments(metric_path(ws, metric.removesuffix("_v1")), m, rubric)
            for m in panel
        }
        for metric, rubric in rubrics.items()
    }
    values: Values = defaultdict(lambda: defaultdict(dict))
    eligible: dict[tuple[str, str], int] = defaultdict(int)
    done: dict[tuple[str, str, str], int] = defaultdict(int)

    def count(metric: str, cfg: str, labels: dict[str, Any], judges: list[str]) -> None:
        eligible[(metric, cfg)] += 1
        for m in judges:
            done[(metric, cfg, m)] += labels.get(m) is not None

    for s in scores:
        item = by_id[s.item_id]
        qs, cfg, iid = s.question_set, s.config, s.item_id
        run = runs[cfg].get(iid)
        key = answer_key(iid, cfg, run.output_answer or "") if run and s.has_answer else None

        def labels(metric: str, key: str = key or "") -> dict[str, str | None]:
            return {m: (judged[metric][m].get(key) or {}).get("label") for m in panel}

        if qs in ("A", "C") and item.truth is not None:
            if key:
                count("masked_correctness", cfg, s.votes.get("masked_correctness", {}), panel)
            values["mc_same"][cfg][iid] = float(s.masked_verdict in ("exact", "same_category"))
            values["mc_exact"][cfg][iid] = float(s.masked_verdict == "exact")
            reference = references.get(iid)
            if reference is not None and scorable(reference):
                z: float | None = SCORE_CAP
                z1: float | None = SCORE_CAP
                if key:
                    outputs = {m: judged["zlog_value"][m].get(key) for m in chat}
                    count("zlog_value", cfg, outputs, chat)
                    read = [o for o in outputs.values() if o is not None]
                    z = z1 = None
                    if read:
                        z = statistics.median(
                            value_score(reference, o, scaled=ZLOG_SCALED) for o in read
                        )
                        z1 = statistics.median(
                            value_score(reference, o, scaled=not ZLOG_SCALED) for o in read
                        )
                if z is not None and z1 is not None:
                    values["zlog"][cfg][iid] = z
                    values["zlog_sat"][cfg][iid] = float(z <= SATISFACTORY)
                    values["zlog_v1"][cfg][iid] = z1
                    values["zlog_v1_sat"][cfg][iid] = float(z1 <= SATISFACTORY)
        if qs in ("B", "C"):
            if key:
                count("factual_consistency", cfg, s.votes.get("factual_consistency", {}), panel)
            values["fc_consistent"][cfg][iid] = float(s.consistency == "consistent")
            for metric, prefix in (("case_alignment", "align"), ("case_alignment_v1", "align_v1")):
                label: str | None = "unanswered"
                if key:
                    votes = labels(metric)
                    count(metric, cfg, votes, panel)
                    label = vote(votes).label
                if label is not None:
                    values[f"{prefix}_aligned"][cfg][iid] = float(label == "aligned")
                    values[f"{prefix}_contra"][cfg][iid] = float(label == "contradicted")
                    if f"{prefix}_ok" in ALL:
                        values[f"{prefix}_ok"][cfg][iid] = float(label in ("aligned", "neutral"))
                        values[f"{prefix}_neutral"][cfg][iid] = float(label == "neutral")
        if qs in ("A", "B") and cfg not in NO_DOCUMENT_CONFIGS:
            label = "not_supported"
            if key and run is not None and run.documents:
                votes = labels("faithfulness")
                count("faithfulness", cfg, votes, panel)
                label = vote(votes).label
            if label is not None:
                values["faith"][cfg][iid] = float(label == "supported")
    coverage: Coverage = {}
    for (metric, cfg), n in eligible.items():
        judges = chat if metric == "zlog_value" else panel
        coverage[(metric, cfg)] = min(done[(metric, cfg, m)] / n for m in judges) if n else 1.0
    return values, {i.item_id: i.diagnosis for i in items}, coverage


def run_values(run: int, panel: list[str]) -> tuple[Values, dict[str, str], Coverage]:
    """As :func:`workspace_values` for both workspaces of one run. Values of a metric and
    configuration that the panel has not finished judging are dropped."""
    index = json.loads((RESULTS / "repeats" / "index.json").read_text(encoding="utf-8"))
    chat = [m for m in panel if m != JEV_MODEL] or list(BenchSettings().judge_models)
    references = load_references(chat)
    merged: Values = defaultdict(lambda: defaultdict(dict))
    diagnoses: dict[str, str] = {}
    coverage: Coverage = {}
    for kind, key in (("ab", "sets_ab"), ("c", "set_c")):
        values, diag, cover = workspace_values(
            Workspace(REPO / index["runs"][str(run)][key]), kind, panel, references
        )
        diagnoses.update(diag)
        coverage.update(cover)
        for metric, per_config in values.items():
            for config, per_item in per_config.items():
                if cover.get((ALL[metric][1], config), 1.0) >= COMPLETE:
                    merged[metric][config].update(per_item)
    return merged, diagnoses, coverage


def scale(metric: str, value: float) -> float:
    return 100 * value if metric in PERCENT else value


def metric_configs(metric: str) -> list[str]:
    return [c for c in REPEATED if not (metric == "faith" and c in NO_DOCUMENT_CONFIGS)]


# --- sensitivity on one run ----------------------------------------------------------------------


def single_run_sensitivity(
    per_config: dict[str, dict[str, float]],
    diagnoses: dict[str, str],
    configs: list[str],
    *,
    n_boot: int = 2000,
    seed: int = 0,
) -> dict[str, Any] | None:
    """Spread of the configurations' means against their bootstrap noise, on shared questions.

    Diagnoses are resampled (questions about one diagnosis are not independent) and the same
    resample is used for every configuration, so differences are paired.
    """
    configs = [c for c in configs if per_config.get(c)]
    if len(configs) < 2:
        return None
    shared = set.intersection(*(set(per_config[c]) for c in configs))
    if not shared:
        return None
    clusters = sorted({diagnoses[i] for i in shared})
    sums: dict[str, dict[str, float]] = {c: defaultdict(float) for c in configs}
    counts: dict[str, int] = defaultdict(int)
    for item in shared:
        counts[diagnoses[item]] += 1
        for c in configs:
            sums[c][diagnoses[item]] += per_config[c][item]
    means = {c: sum(sums[c].values()) / len(shared) for c in configs}
    rng = random.Random(seed)
    draws: dict[str, list[float]] = {c: [] for c in configs}
    for _ in range(n_boot):
        picked = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        total = sum(counts[k] for k in picked)
        for c in configs:
            draws[c].append(sum(sums[c][k] for k in picked) / total)
    se = {c: statistics.pstdev(draws[c]) for c in configs}
    pairs = [(a, b) for i, a in enumerate(configs) for b in configs[i + 1 :]]
    separated = []
    for a, b in pairs:
        diffs = sorted(x - y for x, y in zip(draws[a], draws[b], strict=True))
        low, high = diffs[int(0.025 * (n_boot - 1))], diffs[int(0.975 * (n_boot - 1))]
        if low > 0 or high < 0:
            separated.append((a, b))
    spread = statistics.stdev(means.values())
    noise = statistics.fmean(se.values())
    return {"questions": len(shared), "means": means, "se": se, "spread": spread, "noise": noise,
            "signal_to_noise": spread / noise if noise else None, "pairs": len(pairs),
            "pairs_separated": len(separated), "separated": separated}  # fmt: skip


def print_test(run: int, panel: list[str]) -> dict[str, Any]:
    values, diagnoses, coverage = run_values(run, panel)
    report: dict[str, Any] = {"run": run, "panel": panel, "metrics": {},
                              "titles": {k: v[0] for k, v in ALL.items()}}  # fmt: skip
    print(f"Run {run}, panel {panel}\n")
    print(f"{'metric':52s} {'n':>4s} {'spread':>7s} {'noise':>6s} {'S/N':>5s} {'pairs':>6s}  means")
    for metric, (title, _, _, _) in ALL.items():
        configs = metric_configs(metric)
        result = single_run_sensitivity(values.get(metric, {}), diagnoses, configs)
        if result is None:
            continue
        report["metrics"][metric] = result
        means = "  ".join(f"{scale(metric, result['means'][c]):.1f}" for c in configs)
        print(
            f"{title:52s} {result['questions']:4d} {scale(metric, result['spread']):7.2f} "
            f"{scale(metric, result['noise']):6.2f} {result['signal_to_noise'] or 0:5.2f} "
            f"{result['pairs_separated']:3d}/{result['pairs']:<2d}  {means}"
        )
    print("\nconfigurations:", ", ".join(REPEATED))
    low = {f"{m}/{c}": round(v, 3) for (m, c), v in coverage.items() if v < COMPLETE}
    if low:
        print("not fully judged (left out):", low)
    return report


# --- all runs ------------------------------------------------------------------------------------


def all_runs(panel: list[str]) -> dict[str, dict[str, dict[int, float]]]:
    """metric -> config -> run -> the run's mean (complete runs only)."""
    index = json.loads((RESULTS / "repeats" / "index.json").read_text(encoding="utf-8"))
    table: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for run_text in sorted(index["runs"], key=int):
        values, _, _ = run_values(int(run_text), panel)
        for metric, per_config in values.items():
            for config, per_item in per_config.items():
                if per_item:
                    table[metric][config][int(run_text)] = statistics.fmean(per_item.values())
    return table


def across_run_sensitivity(
    per_config: dict[str, dict[int, float]], configs: list[str]
) -> dict[str, Any] | None:
    """Between-configuration spread against run-to-run noise, from the per-run means."""
    groups = {c: list(per_config[c].values()) for c in configs if len(per_config.get(c, {})) > 1}
    if len(groups) < 2:
        return None
    means = {c: statistics.fmean(v) for c, v in groups.items()}
    sds = {c: statistics.stdev(v) for c, v in groups.items()}
    within = statistics.fmean(sd**2 for sd in sds.values())
    between = statistics.variance(means.values())
    names = list(groups)
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1 :]]
    separated = []
    for a, b in pairs:
        se = (sds[a] ** 2 / len(groups[a]) + sds[b] ** 2 / len(groups[b])) ** 0.5
        # Welch's t; |t| > 2.3 is p < 0.05 for the smallest number of runs used here (6 a side).
        if se and abs(means[a] - means[b]) / se > 2.3:
            separated.append((a, b))
    return {"spread": between**0.5, "run_sd": within**0.5,
            "signal_to_noise": (between / within) ** 0.5 if within else None,
            "runs": min(len(v) for v in groups.values()),
            "pairs": len(pairs), "pairs_separated": len(separated)}  # fmt: skip


def cell(metric: str, runs: dict[int, float]) -> str:
    if not runs:
        return "–"
    values = [scale(metric, v) for v in runs.values()]
    digits = 2 if metric in ("zlog", "zlog_v1") else 1
    suffix = "%" if metric in PERCENT else ""
    if len(values) == 1:
        return f"{values[0]:.{digits}f}{suffix}"
    return f"{statistics.fmean(values):.{digits}f} ± {statistics.stdev(values):.{digits}f}{suffix}"


def build_full() -> dict[str, Any]:
    panel3 = list(BenchSettings().judge_models)
    data: dict[str, Any] = {"panels": {}, "order": [[c, name] for c, name, _ in ORDER],
                            "metrics": {k: v[0] for k, v in ALL.items()},
                            "kept": list(METRICS), "variants": list(VARIANTS)}  # fmt: skip
    for name, panel in (("three_judges", panel3), ("with_jev", [*panel3, JEV_MODEL])):
        table = all_runs(panel)
        data["panels"][name] = {
            "panel": panel,
            "cells": {m: {c: cell(m, table[m].get(c, {})) for c, _, _ in ORDER} for m in ALL},
            "n_runs": {m: {c: len(table[m].get(c, {})) for c, _, _ in ORDER} for m in ALL},
            "sensitivity": {m: across_run_sensitivity(table[m], metric_configs(m)) for m in ALL},
            "runs": {m: {c: {str(r): v for r, v in rv.items()} for c, rv in per.items()}
                     for m, per in table.items()},
        }  # fmt: skip
    return data


def markdown_table(data: dict[str, Any], panel_name: str) -> str:
    panel = data["panels"][panel_name]
    head = ["Configuration", *(METRICS[m][0] for m in METRICS)]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for config, name in data["order"]:
        row = [name]
        for m in METRICS:
            n = panel["n_runs"][m][config]
            row.append(panel["cells"][m][config] + (f" (n={n})" if n > 1 else ""))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["test", "full"])
    parser.add_argument("--run", type=int, default=2)
    parser.add_argument("--panel", help="Comma-separated judge models; default: the panel.")
    parser.add_argument("--save", type=Path, help="test: also write the result as JSON here.")
    args = parser.parse_args()
    if args.mode == "test":
        panel = args.panel.split(",") if args.panel else list(BenchSettings().judge_models)
        report = print_test(args.run, panel)
        if args.save:
            args.save.parent.mkdir(parents=True, exist_ok=True)
            args.save.write_text(json.dumps(report, indent=1), encoding="utf-8")
        return
    data = build_full()
    SHARED.mkdir(parents=True, exist_ok=True)
    (SHARED / "answer_metrics.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    parts = ["# Answer metrics: old and new, all configurations\n",
             "Mean ± SD over the runs the whole panel judged (n = number of runs).\n"]  # fmt: skip
    titles = (("three_judges", "Three judges"), ("with_jev", "With the Jev decision model added"))
    for name, title in titles:
        panel = data["panels"][name]
        parts += [f"## {title}\n", f"Panel: {', '.join(panel['panel'])}\n",
                  markdown_table(data, name) + "\n"]  # fmt: skip
    (SHARED / "answer_metrics.md").write_text("\n".join(parts), encoding="utf-8")
    print("\n".join(parts))
    print(f"Wrote {SHARED / 'answer_metrics.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
