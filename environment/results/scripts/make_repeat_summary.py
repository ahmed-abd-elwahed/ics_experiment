"""Build the repeated-runs table: each label's percentage as mean ± standard deviation over runs.

Usage: python environment/results/scripts/make_repeat_summary.py [REPEATS_DIR]
Reads environment/results/repeats/index.json (which workspaces hold run 1..N) and every run's
records and judgments; no API calls. Writes repeat_summary.md, .html, .json, and .pdf into
REPEATS_DIR (the PDF is printed from the HTML by headless Google Chrome).

For each configuration and run: every label's share of all questions in the set (the judge
panel's voted label), the total cost of all its questions, and the mean answer time. The table
shows the mean and the sample standard deviation (n - 1) of these per-run values. A run counts
for a configuration only when all its questions ran successfully and every answer is judged;
incomplete runs are listed, not averaged. Masked correctness "same category" includes exact.
"""

from __future__ import annotations

import html
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

from bench.config import BenchSettings
from bench.judge import SET_METRICS
from bench.report import CONSISTENCY_LABELS, METRICS, Score, build_scores
from bench.schemas import Item
from bench.workspace import Workspace, read_models

RESULTS = Path(__file__).resolve().parents[1]
REPEATS = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS / "repeats"
REPO = RESULTS.parents[1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# (configuration, row name, workspace kind)
ORDER = [
    ("gemini_knowledge", "1. Gemini 3 Flash knowledge, no search (gemini-3-flash-preview)", "ab"),
    ("current", "2. Current without changes 1–4 (Europe PMC + LitSense)", "ab"),
    ("improved_1to4", "3. Current with changes 1–4 (Europe PMC + LitSense)", "ab"),
    ("openrouter_exa_instant", "4. OpenRouter search: Exa instant, DeepSeek v4 Flash", "ab"),
    ("openrouter_parallel_basic", "5. OpenRouter search: Parallel basic, DeepSeek v4 Flash", "ab"),
    ("openrouter_perplexity", "6. OpenRouter search: Perplexity, DeepSeek v4 Flash", "ab"),
    ("openrouter_google", "7. OpenRouter search: Google (native), Gemini 3.1 Flash Lite", "ab"),
    ("openrouter_openai", "8. OpenRouter search: OpenAI (native), GPT-6-luna", "ab"),
    ("case_information", "9. Case information only, no retrieval (DeepSeek v4 Flash 0731)", "c"),
]
GROUPS = [
    ("Masked correctness", "mc", ["same_category", "different_category", "not_comparable",
                                   "no_label"]),
    ("Factual consistency", "fc", [*CONSISTENCY_LABELS, "no_label"]),
]  # fmt: skip
VERDICTS = {"masked_correctness": "masked_verdict", "factual_consistency": "consistency"}


def label_name(label: str) -> str:
    if label == "no_label":
        return "no label*"
    if label == "same_category":
        return "same category (incl. exact)†"
    return label.replace("_", " ")


def metric_key(kind: str, key: str, label: str) -> str:
    return f"{key}_c_{label}" if kind == "c" else f"{key}_{label}"


def run_values(scores: list[Score], kind: str) -> dict[str, float] | None:
    """One run of one configuration: label shares (%), total cost, mean time; None if the run
    is incomplete (a question did not run, or an answer is not judged)."""
    if not scores or any(not s.ran for s in scores):
        return None
    for s in scores:
        if s.has_answer and any(
            getattr(s, VERDICTS[m]) is None for m in SET_METRICS[s.question_set]
        ):
            return None
    values: dict[str, float] = {}
    for _, key, labels in GROUPS:
        for label in labels:
            name = metric_key(kind, key, label)
            fn, qs = METRICS[name][1], METRICS[name][2]
            shares = [fn(s) or 0.0 for s in scores if s.question_set == qs]
            values[f"{key}_{label}"] = 100 * sum(shares) / len(shares)
    values["total_cost_usd"] = sum(s.total_cost for s in scores)
    values["mean_time_s"] = statistics.fmean(s.wall_time_s for s in scores)
    values["best_guesses"] = float(sum(s.path == "best_guess" for s in scores))
    return values


def collect(
    panel: list[str],
) -> tuple[dict[str, dict[int, dict[str, float]]], dict[str, list[int]]]:
    """config -> run -> values, and config -> incomplete runs."""
    index = json.loads((REPEATS / "index.json").read_text(encoding="utf-8"))
    per_config: dict[str, dict[int, dict[str, float]]] = {c: {} for c, _, _ in ORDER}
    incomplete: dict[str, list[int]] = {c: [] for c, _, _ in ORDER}
    for run_text, paths in sorted(index["runs"].items(), key=lambda kv: int(kv[0])):
        run = int(run_text)
        for kind, key in (("ab", "sets_ab"), ("c", "set_c")):
            ws = Workspace(REPO / paths[key])
            configs = [c for c, _, k in ORDER if k == kind and ws.run_file(c).exists()]
            if not configs:
                continue
            scores = build_scores(ws, read_models(ws.items, Item), configs, panel)
            for config in configs:
                values = run_values([s for s in scores if s.config == config], kind)
                if values is None:
                    incomplete[config].append(run)
                else:
                    per_config[config][run] = values
    return per_config, incomplete


def missing_verdicts(panel: list[str]) -> int:
    """Judge calls (answer, judge) of the repeat runs whose latest attempt still failed."""
    missing = 0
    for path in REPEATS.glob("run_*/*/judge/*.jsonl"):
        latest: dict[tuple[str, str], str] = {}
        for line in path.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                record = json.loads(line)
                if record["judge_model"] in panel:
                    latest[(record["answer_key"], record["judge_model"])] = record["status"]
        missing += sum(status != "ok" for status in latest.values())
    return missing


def stats(values: list[float]) -> tuple[float, float | None]:
    return statistics.fmean(values), (statistics.stdev(values) if len(values) > 1 else None)


def cell(values: list[float], fmt: str, suffix: str = "", prefix: str = "") -> str:
    if not values:
        return "–"
    mean, sd = stats(values)
    if sd is None:
        return f"{prefix}{mean:{fmt}}{suffix}"
    return f"{prefix}{mean:{fmt}} ± {sd:{fmt}}{suffix}"


def cost_values(runs: dict[int, dict[str, float]]) -> list[float]:
    """Per-run costs at one price level: OpenRouter raised the environment model's price after
    run 1, so with later runs available run 1 is left out of the cost (not of the other
    columns)."""
    later = [v["total_cost_usd"] for r, v in runs.items() if r != 1]
    return later or [v["total_cost_usd"] for v in runs.values()]


def table_rows(per_config: dict[str, dict[int, dict[str, float]]]) -> list[list[str]]:
    rows = []
    for config, name, _ in ORDER:
        runs = per_config[config]
        if not runs:
            continue
        cells = [name, str(len(runs))]
        for _, key, labels in GROUPS:
            for label in labels:
                cells.append(cell([v[f"{key}_{label}"] for v in runs.values()], ".1f", "%"))
        cells.append(cell(cost_values(runs), ".3f", prefix="$"))
        cells.append(cell([v["mean_time_s"] for v in runs.values()], ".1f"))
        rows.append(cells)
    return rows


def markdown(rows: list[list[str]]) -> str:
    first = ["Metric →", ""]
    for title, _, labels in GROUPS:
        first += [title] + [""] * (len(labels) - 1)
    first += ["Environment cost and time", ""]
    second = ["Environment configuration ↓ / label →", "Runs"]
    second += [label_name(label) for _, _, labels in GROUPS for label in labels]
    second += ["Total cost per run (USD)‡", "Average answer time (s)"]
    lines = ["| " + " | ".join(first) + " |", "|" + "---|" * len(first),
             "| " + " | ".join(second) + " |"]  # fmt: skip
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def html_page(rows: list[list[str]], counts: dict[str, int], notes: list[str]) -> str:
    head1 = ['<th rowspan="2" class="cfg">Environment configuration</th>',
             '<th rowspan="2">Runs</th>']  # fmt: skip
    head2 = []
    for title, _key, labels in GROUPS:
        head1.append(f'<th colspan="{len(labels)}" class="group">{html.escape(title)}</th>')
        head2 += [f"<th>{html.escape(label_name(label))}</th>" for label in labels]
    head1.append('<th colspan="2" class="group">Environment cost and time</th>')
    head2 += ["<th>Total cost per run (USD)‡</th>", "<th>Average answer time (s)</th>"]
    firsts = {2, 2 + len(GROUPS[0][2]), 2 + len(GROUPS[0][2]) + len(GROUPS[1][2])}
    body = []
    for r in rows:
        cells = [f'<td class="cfg">{html.escape(r[0])}</td>', f"<td>{r[1]}</td>"]
        for i, value in enumerate(r[2:], 2):
            mean, _, sd = value.partition(" ± ")
            shown = html.escape(mean) + (
                f'<span class="sd"> ± {html.escape(sd)}</span>' if sd else ""
            )
            cells.append(f'<td class="{"first" if i in firsts else ""}">{shown}</td>')
        row_class = ' class="setc"' if r[0].startswith("9.") else ""
        body.append(f"<tr{row_class}>" + "".join(cells) + "</tr>")
    note_items = "".join(f"<li>{html.escape(n)}</li>" for n in notes)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Environment benchmark: repeated runs</title>
<style>
  @page {{ size: A4 landscape; margin: 11mm; }}
  body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1b1b1b;
         font-size: 10.5px; }}
  h1 {{ font-size: 18px; margin: 0 0 4px; }}
  p.sub {{ margin: 0 0 10px; color: #555; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #cfcfcf; padding: 5px 5px; text-align: center; }}
  thead tr:first-child th {{ background: #e9eef6; font-size: 11.5px; }}
  thead tr:nth-child(2) th {{ background: #f4f6fa; font-weight: 600; }}
  th.group, td.first {{ border-left: 2px solid #8a94a6; }}
  td.cfg, th.cfg {{ text-align: left; }}
  td.cfg {{ font-weight: 600; min-width: 215px; }}
  td {{ white-space: nowrap; }}
  td.cfg {{ white-space: normal; }}
  span.sd {{ color: #666; }}
  tbody tr:nth-child(even) td {{ background-color: #fafafa; }}
  tr.setc td {{ border-top: 2px solid #8a94a6; }}
  ul {{ margin: 10px 0 0; padding-left: 16px; color: #333; }}
  li {{ margin: 3px 0; }}
</style></head><body>
<h1>Environment benchmark: repeated runs (mean ± standard deviation)</h1>
<p class="sub">Each value is the mean ± the standard deviation, over the runs, of a per-run
figure: the percent of all questions in the set with that voted label, the total cost of the
run, and the mean answer time. Configurations 1–8: masked correctness on set A ({counts["A"]}
questions with a value hidden from the case), factual consistency on set B ({counts["B"]}
questions the case never answers). Configuration 9: both on set C ({counts["C"]} questions the
case answers).</p>
<table><thead><tr>{"".join(head1)}</tr><tr>{"".join(head2)}</tr></thead>
<tbody>{"".join(body)}</tbody></table>
<ul>{note_items}</ul>
</body></html>
"""


def main() -> None:
    panel = BenchSettings().judge_models
    per_config, incomplete = collect(panel)
    index = json.loads((REPEATS / "index.json").read_text(encoding="utf-8"))
    first = index["runs"]["1"]
    counts: dict[str, int] = {}
    for key in ("sets_ab", "set_c"):
        for item in read_models(Workspace(REPO / first[key]).items, Item):
            counts[item.question_set] = counts.get(item.question_set, 0) + 1
    rows = table_rows(per_config)
    skipped = {c: runs for c, runs in incomplete.items() if runs}
    notes = [
        "Every run answers the same questions; runs 2 and later search anew (no cached search "
        "results). The standard deviation is the sample standard deviation (n − 1) across runs.",
        "Configurations 7 and 8 (native Google and OpenAI search) were run once, so they have no "
        "standard deviation, and their cost is run 1's, at the earlier (lower) DeepSeek price.",
        f"Judge panel: {', '.join(panel)}; each answer's label is the majority vote (with no "
        f"majority, the first judge decides).",
        "† Same category (incl. exact): answers at least in the true value's category (exact + "
        "same category). With different category, not comparable, and no label it sums to 100%.",
        "* No label: medsim gave no answer (almost all are questions its query builder refuses), "
        "or the run failed; it is not a judge label.",
        "Total cost per run: every environment component for all questions of the configuration "
        "(medsim Stages A–C, search fees, the search or knowledge model's tokens), from "
        "OpenRouter's usage.cost; judging is not included. Average answer time: mean wall time "
        "per question.",
        "‡ Cost is the mean ± SD over runs 2 and later only: after run 1 (2026-09-29) OpenRouter "
        "raised deepseek/deepseek-v4-flash-0731's output price from $0.32 to $1.28 per million "
        "tokens, so run 1's cost is at another price level. Run 1 cost: "
        + "; ".join(
            f"{name.split('.')[0]}: ${per_config[c][1]['total_cost_usd']:.2f}"
            for c, name, _ in ORDER
            if 1 in per_config[c] and len(per_config[c]) > 1
        )
        + " (by row number). Percentages and time use every run.",
        "Run 1 reached the best-guess fallback through a replay of its declined answers on the "
        "same documents; in runs 2 and later it is built into medsim.",
    ]
    missing = missing_verdicts(panel)
    if missing:
        notes.append(
            f"{missing} of the judge calls in runs 2 and later failed on every attempt "
            "(qwen/qwen3.8-flash rate limits); those answers were voted on by the other two "
            "judges."
        )
    if skipped:
        notes.append(
            "Incomplete runs (a question failed or an answer is not judged), not averaged: "
            + "; ".join(f"{c}: run {', '.join(map(str, r))}" for c, r in skipped.items())
            + "."
        )
    md = markdown(rows)
    (REPEATS / "repeat_summary.md").write_text(
        "# Environment benchmark: repeated runs\n\n" + md + "\n\n"
        + "\n".join(f"- {n}" for n in notes) + "\n",
        encoding="utf-8",
    )  # fmt: skip
    data: dict[str, Any] = {"panel": panel, "question_counts": counts, "incomplete": skipped,
                            "configs": {}}  # fmt: skip
    for config, runs in per_config.items():
        if not runs:
            continue
        keys = next(iter(runs.values())).keys()
        summary = {}
        for k in keys:
            mean, sd = stats([v[k] for v in runs.values()])
            summary[k] = {"mean": mean, "sd": sd}
        data["configs"][config] = {"runs": {str(r): v for r, v in runs.items()},
                                   "summary": summary}  # fmt: skip
    (REPEATS / "repeat_summary.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    page = REPEATS / "repeat_summary.html"
    page.write_text(html_page(rows, counts, notes), encoding="utf-8")
    pdf = REPEATS / "repeat_summary.pdf"
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", page.as_uri()],
        check=True, capture_output=True,
    )  # fmt: skip
    print(md)
    print(f"\nWrote {pdf}", file=sys.stderr)


if __name__ == "__main__":
    main()
