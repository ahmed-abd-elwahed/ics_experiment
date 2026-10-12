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
share is over the full question set.
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
REPEATED = [
    c for c, _, k in ORDER if k == "ab" and not c.startswith(("openrouter_g", "openrouter_openai"))
]
# metric key -> (title, question sets on ab workspaces, higher is better, old or new)
METRICS: dict[str, tuple[str, str, bool, str]] = {
    "mc_same": ("Masked correctness: same category (incl. exact), %", "A", True, "old"),
    "mc_exact": ("Masked correctness: exact, %", "A", True, "old"),
    "fc_consistent": ("Factual consistency: consistent, %", "B", True, "old"),
    "zlog": ("Zlog z-score: mean |z| (capped at 3)", "A", False, "new"),
    "zlog_sat": ("Zlog z-score: satisfactory (|z| ≤ 2), %", "A", True, "new"),
    "faith": ("Faithfulness: supported, %", "AB", True, "new"),
    "align_aligned": ("Case alignment: aligned, %", "B", True, "new"),
    "align_contra": ("Case alignment: contradicted, %", "B", False, "new"),
}
# The other version of the two revised metrics, kept for the comparison in the test stage.
VARIANTS: dict[str, tuple[str, str, bool, str]] = {
    "zlog_v1": ("Zlog z-score, first version: mean |z|", "A", False, "new"),
    "zlog_v1_sat": ("Zlog z-score, first version: satisfactory, %", "A", True, "new"),
    "align_v1_aligned": ("Case alignment, first version: aligned, %", "B", True, "new"),
    "align_v1_contra": ("Case alignment, first version: contradicted, %", "B", False, "new"),
}
PERCENT = {k for k in METRICS | VARIANTS if k not in ("zlog", "zlog_v1")}
# The versions kept after the test stage (see the README): the revised zlog scale and the
# revised case alignment rubric.
ZLOG_SCALED = True
ALIGNMENT_RUBRIC = "m2"

Values = dict[str, dict[str, dict[str, float]]]  # metric -> config -> item id -> value


def workspace_values(
    ws: Workspace, kind: str, panel: list[str], references: dict[str, Any]
) -> tuple[Values, dict[str, str], dict[str, int]]:
    """Per-question values of every metric in one workspace, the questions' diagnoses, and how
    many answers lack a judgment (per metric)."""
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
    missing: dict[str, int] = defaultdict(int)
    for s in scores:
        item = by_id[s.item_id]
        qs, cfg, iid = s.question_set, s.config, s.item_id
        run = runs[cfg].get(iid)
        key = answer_key(iid, cfg, run.output_answer or "") if run and s.has_answer else None

        def panel_label(metric: str, key: str = key or "") -> str | None:
            return vote({m: (judged[metric][m].get(key) or {}).get("label") for m in panel}).label

        if qs in ("A", "C") and item.truth is not None:
            if key and s.masked_verdict is None:
                missing["masked_correctness"] += 1
            values["mc_same"][cfg][iid] = float(s.masked_verdict in ("exact", "same_category"))
            values["mc_exact"][cfg][iid] = float(s.masked_verdict == "exact")
            reference = references.get(iid)
            if reference is not None and scorable(reference):
                if key is None:
                    z: float | None = SCORE_CAP
                else:
                    outputs = [
                        judged["zlog_value"][m][key] for m in chat if key in judged["zlog_value"][m]
                    ]
                    read = [value_score(reference, o, scaled=ZLOG_SCALED) for o in outputs]
                    z = statistics.median(read) if read else None
                    other = [value_score(reference, o, scaled=not ZLOG_SCALED) for o in outputs]
                    if other:
                        z1 = statistics.median(other)
                        values["zlog_v1"][cfg][iid] = z1
                        values["zlog_v1_sat"][cfg][iid] = float(z1 <= SATISFACTORY)
                if z is None:
                    missing["zlog_value"] += 1
                else:
                    values["zlog"][cfg][iid] = z
                    values["zlog_sat"][cfg][iid] = float(z <= SATISFACTORY)
                    if key is None:
                        values["zlog_v1"][cfg][iid] = SCORE_CAP
                        values["zlog_v1_sat"][cfg][iid] = 0.0
        if qs in ("B", "C"):
            if key and s.consistency is None:
                missing["factual_consistency"] += 1
            values["fc_consistent"][cfg][iid] = float(s.consistency == "consistent")
            label = panel_label("case_alignment") if key else "unanswered"
            if label is None:
                missing["case_alignment"] += 1
            else:
                values["align_aligned"][cfg][iid] = float(label == "aligned")
                values["align_contra"][cfg][iid] = float(label == "contradicted")
            first = panel_label("case_alignment_v1") if key else "unanswered"
            if first is not None:
                values["align_v1_aligned"][cfg][iid] = float(first == "aligned")
                values["align_v1_contra"][cfg][iid] = float(first == "contradicted")
        if qs in ("A", "B") and cfg not in NO_DOCUMENT_CONFIGS:
            if key is None or run is None or not run.documents:
                values["faith"][cfg][iid] = 0.0
            else:
                label = panel_label("faithfulness")
                if label is None:
                    missing["faithfulness"] += 1
                else:
                    values["faith"][cfg][iid] = float(label == "supported")
    return values, {i.item_id: i.diagnosis for i in items}, dict(missing)


def run_values(run: int, panel: list[str]) -> tuple[Values, dict[str, str], dict[str, int]]:
    index = json.loads((RESULTS / "repeats" / "index.json").read_text(encoding="utf-8"))
    references = load_references(
        [m for m in panel if m != JEV_MODEL] or BenchSettings().judge_models
    )
    merged: Values = defaultdict(lambda: defaultdict(dict))
    diagnoses: dict[str, str] = {}
    missing: dict[str, int] = defaultdict(int)
    for kind, key in (("ab", "sets_ab"), ("c", "set_c")):
        values, diag, miss = workspace_values(
            Workspace(REPO / index["runs"][str(run)][key]), kind, panel, references
        )
        diagnoses.update(diag)
        for metric, per_config in values.items():
            for config, per_item in per_config.items():
                merged[metric][config].update(per_item)
        for metric, n in miss.items():
            missing[metric] += n
    return merged, diagnoses, dict(missing)


def scale(metric: str, value: float) -> float:
    return 100 * value if metric in PERCENT else value


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
    values, diagnoses, missing = run_values(run, panel)
    report: dict[str, Any] = {
        "run": run,
        "panel": panel,
        "missing_judgments": missing,
        "metrics": {},
    }
    print(f"Run {run}, panel {panel}; answers without a judgment: {missing or 'none'}\n")
    print(f"{'metric':52s} {'n':>4s} {'spread':>7s} {'noise':>6s} {'S/N':>5s} {'pairs':>6s}  means")
    for metric, (title, _, _, _) in (METRICS | VARIANTS).items():
        configs = [c for c in REPEATED if not (metric == "faith" and c in NO_DOCUMENT_CONFIGS)]
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
    return report


# --- all runs ------------------------------------------------------------------------------------


def all_runs(panel: list[str]) -> tuple[dict[str, dict[str, dict[int, float]]], dict[str, int]]:
    """metric -> config -> run -> the run's mean, and missing judgments per metric."""
    index = json.loads((RESULTS / "repeats" / "index.json").read_text(encoding="utf-8"))
    table: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    missing: dict[str, int] = defaultdict(int)
    for run_text in sorted(index["runs"], key=int):
        values, _, miss = run_values(int(run_text), panel)
        for metric, n in miss.items():
            missing[metric] += n
        for metric, per_config in values.items():
            for config, per_item in per_config.items():
                if per_item:
                    table[metric][config][int(run_text)] = statistics.fmean(per_item.values())
    return table, dict(missing)


def across_run_sensitivity(
    per_config: dict[str, dict[int, float]], configs: list[str]
) -> dict[str, Any] | None:
    """Between-configuration spread against run-to-run noise, from the per-run means."""
    groups = {c: list(per_config[c].values()) for c in configs if len(per_config.get(c, {})) > 1}
    if len(groups) < 2:
        return None
    means = {c: statistics.fmean(v) for c, v in groups.items()}
    sds = {c: statistics.stdev(v) for c, v in groups.items()}
    within = statistics.fmean(sd**2 for sd in sds.values())  # pooled variance (equal n)
    n = statistics.fmean(len(v) for v in groups.values())
    between = statistics.variance(means.values())
    names = list(groups)
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1 :]]
    separated = []
    for a, b in pairs:
        se = (sds[a] ** 2 / len(groups[a]) + sds[b] ** 2 / len(groups[b])) ** 0.5
        # Welch's t at about 18 degrees of freedom: |t| > 2.10 is p < 0.05.
        if se and abs(means[a] - means[b]) / se > 2.10:
            separated.append((a, b))
    return {"spread": between**0.5, "run_sd": within**0.5,
            "signal_to_noise": (between / within) ** 0.5 if within else None,
            "f": n * between / within if within else None,
            "pairs": len(pairs), "pairs_separated": len(separated)}  # fmt: skip


def cell(metric: str, runs: dict[int, float]) -> str:
    if not runs:
        return "–"
    values = [scale(metric, v) for v in runs.values()]
    digits = 2 if metric == "zlog" else 1
    suffix = "%" if metric in PERCENT else ""
    if len(values) == 1:
        return f"{values[0]:.{digits}f}{suffix}"
    return f"{statistics.fmean(values):.{digits}f} ± {statistics.stdev(values):.{digits}f}{suffix}"


def build_full() -> dict[str, Any]:
    panel3 = list(BenchSettings().judge_models)
    data: dict[str, Any] = {"panels": {}, "order": [[c, name] for c, name, _ in ORDER],
                            "metrics": {k: v[0] for k, v in METRICS.items()}}  # fmt: skip
    for name, panel in (("three_judges", panel3), ("with_jev", [*panel3, JEV_MODEL])):
        table, missing = all_runs(panel)
        cells = {m: {c: cell(m, table[m].get(c, {})) for c, _, _ in ORDER} for m in METRICS}
        sensitivity = {}
        for m in METRICS:
            configs = [c for c in REPEATED if not (m == "faith" and c in NO_DOCUMENT_CONFIGS)]
            sensitivity[m] = across_run_sensitivity(table[m], configs)
        data["panels"][name] = {
            "panel": panel, "missing_judgments": missing, "cells": cells,
            "sensitivity": sensitivity,
            "runs": {m: {c: {str(r): v for r, v in rv.items()} for c, rv in per.items()}
                     for m, per in table.items()},
        }  # fmt: skip
    return data


def markdown_table(data: dict[str, Any], panel_name: str) -> str:
    cells = data["panels"][panel_name]["cells"]
    head = ["Configuration", *(METRICS[m][0] for m in METRICS)]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for config, name in data["order"]:
        lines.append("| " + " | ".join([name, *(cells[m][config] for m in METRICS)]) + " |")
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
    parts = ["# Answer metrics: old and new, all configurations\n"]
    for name, title in (
        ("three_judges", "Three judges"),
        ("with_jev", "With the Jev decision model added"),
    ):
        panel = data["panels"][name]
        parts += [f"## {title}\n", f"Panel: {', '.join(panel['panel'])}\n",
                  markdown_table(data, name) + "\n"]  # fmt: skip
        if panel["missing_judgments"]:
            parts.append(f"Answers without a judgment: {panel['missing_judgments']}\n")
    (SHARED / "answer_metrics.md").write_text("\n".join(parts), encoding="utf-8")
    print("\n".join(parts))
    print(f"Wrote {SHARED / 'answer_metrics.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
