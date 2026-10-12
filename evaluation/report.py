"""Build the results report (HTML and PDF) from an experiment record and its evaluation.

    .venv/bin/python -m evaluation.report records/<record>.json

Reads ``<record>.json`` and ``<record>.eval.json``; makes no API calls. Writes
``<record>.report.html`` and ``.pdf`` next to them (the PDF is printed from the HTML by
headless Google Chrome).
"""

from __future__ import annotations

import argparse
import html
import json
import math
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiment.record import ExperimentRecord, load_record

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOWN = ("hit_rate@1", "hit_rate@3", "hit_rate@5", "hit_rate@10", "ndcg@10", "mrr")
COLOURS = ("#1f2a5a", "#c2410c", "#0f766e", "#7c3aed", "#b45309", "#475569")
LABELS = {"ndcg@10": "nDCG@10", "mrr": "MRR"}
TITLES = {
    "hypothesis": "1. Hypothesis-driven",
    "knowledge": "2. Knowledge-driven",
    "gut": "3. Gut feeling",
    "channel": "4. Channel-based",
    "sequence": "5. Sequence-based",
}

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font: 10.5pt/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #141413; }
h1 { font-size: 19pt; margin: 0 0 2pt; } h2 { font-size: 13pt; margin: 18pt 0 6pt; }
p { margin: 4pt 0; } .lead { color: #444; } small, .note { color: #555; font-size: 9pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9.5pt; }
th, td { padding: 4pt 6pt; border-bottom: 0.5pt solid #cfd3d9; text-align: right; }
th:first-child, td:first-child { text-align: left; } th { font-weight: 600; background: #f1f2f4; }
td.best { font-weight: 700; } ul { margin: 4pt 0; padding-left: 16pt; } li { margin: 2pt 0; }
svg text { font: 9pt -apple-system, "Helvetica Neue", Arial, sans-serif; fill: #141413; }
h2 { break-after: avoid; } table, figure, ul { break-inside: avoid; } figure { margin: 6pt 0; }
td:first-child, th:first-child { white-space: nowrap; }
"""


def wilson(p: float, n: int) -> tuple[float, float]:
    """The 95% Wilson interval of a proportion."""
    if n == 0:
        return 0.0, 0.0
    z = 1.96
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar(a: dict[str, bool], b: dict[str, bool]) -> tuple[int, int, float]:
    """Cases only ``a`` hit, cases only ``b`` hit, and the exact two-sided McNemar p-value."""
    only_a = sum(a[c] and not b[c] for c in a)
    only_b = sum(b[c] and not a[c] for c in a)
    n = only_a + only_b
    if n == 0:
        return 0, 0, 1.0
    tail = sum(math.comb(n, i) for i in range(min(only_a, only_b) + 1)) / 2**n
    return only_a, only_b, min(1.0, 2 * tail)


def paired(evaluation: dict[str, Any]) -> str:
    """Every pair of strategies compared on the same cases, at k = 1 and k = 10."""
    keys = list(evaluation["by_strategy"])
    hits: dict[int, dict[str, dict[str, bool]]] = {k: {key: {} for key in keys} for k in (1, 10)}
    for row in evaluation["case_runs"]:
        for k in (1, 10):
            hit = row["rank"] is not None and row["rank"] <= k
            hits[k][row["strategy"]][row["case_id"]] = hit
    pairs = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1 :]]
    rows = ""
    for a, b in pairs:
        cells = ""
        for k in (1, 10):
            only_a, only_b, p = mcnemar(hits[k][a], hits[k][b])
            mark = ' class="best"' if p < 0.05 / max(1, len(pairs)) else ""
            cells += f"<td>{only_a} / {only_b}</td><td{mark}>{p:.3f}</td>"
        rows += f"<tr><td>{html.escape(title(a))} vs {html.escape(title(b))}</td>{cells}</tr>"
    return (
        "<table><tr><th>Pair (first vs second)</th><th>@1: cases only the first / only the "
        "second hit</th><th>p</th><th>@10: only the first / only the second</th><th>p</th></tr>"
        f"{rows}</table>"
        f'<p class="note">Exact McNemar test on the same {len(hits[1][keys[0]])} cases. With '
        f"{len(pairs)} comparisons, a p-value below {0.05 / max(1, len(pairs)):.3f} (bold) "
        "holds after a Bonferroni correction; values between that and 0.05 are suggestive only."
        "</p>"
    )


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def title(key: str) -> str:
    return TITLES.get(key, key)


def chart(by_strategy: dict[str, Any]) -> str:
    """Hit rate at k = 1..10, one line per strategy, labelled at its right end."""
    left, top, width, height = 44, 12, 430, 210
    top_value = max(s["metrics"]["hit_rate@10"] for s in by_strategy.values())
    y_max = max(0.1, math.ceil(top_value * 10 + 1e-9) / 10)

    def x(k: int) -> float:
        return left + (k - 1) * width / 9

    def y(v: float) -> float:
        return float(top + height - v / y_max * height)

    parts = [f'<svg viewBox="0 0 640 {top + height + 40}" width="100%" role="img" '
             'aria-label="Hit rate at k by strategy">']  # fmt: skip
    for i in range(round(y_max * 10) + 1):
        v = i / 10
        parts.append(f'<line x1="{left}" x2="{left + width}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
                     'stroke="#d8dce2" stroke-width="0.6"/>')  # fmt: skip
        parts.append(f'<text x="{left - 6}" y="{y(v) + 3:.1f}" text-anchor="end">{100 * v:.0f}%'
                     "</text>")  # fmt: skip
    for k in range(1, 11):
        parts.append(f'<text x="{x(k):.1f}" y="{top + height + 15}" text-anchor="middle">{k}'
                     "</text>")  # fmt: skip
    parts.append(f'<text x="{left + width / 2}" y="{top + height + 32}" text-anchor="middle">'
                 "k: the true diagnosis is among the first k diagnoses</text>")  # fmt: skip
    ends: list[tuple[float, str, str]] = []
    for (key, summary), colour in zip(by_strategy.items(), COLOURS, strict=False):
        values = [summary["metrics"][f"hit_rate@{k}"] for k in range(1, 11)]
        points = " ".join(f"{x(k):.1f},{y(v):.1f}" for k, v in enumerate(values, 1))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{colour}" '
                     'stroke-width="1.8"/>')  # fmt: skip
        parts.extend(f'<circle cx="{x(k):.1f}" cy="{y(v):.1f}" r="2.2" fill="{colour}"/>'
                     for k, v in enumerate(values, 1))  # fmt: skip
        ends.append((y(values[-1]), f"{title(key)}  {pct(values[-1])}", colour))
    ends.sort()
    placed = top - 12.0
    for at, label, colour in ends:  # labels pushed apart so they never overlap
        placed = max(at, placed + 12)
        parts.append(f'<text x="{left + width + 8}" y="{placed + 3:.1f}" fill="{colour}" '
                     f'style="fill:{colour}">{html.escape(label)}</text>')  # fmt: skip
    return "".join(parts) + "</svg>"


def run_facts(record: ExperimentRecord, key: str) -> dict[str, Any]:
    runs = [run for run in record.case_runs if run.strategy == key]
    iterations = [it for run in runs for it in run.iterations]
    calls = [c for it in iterations for c in it.strategy_llm_calls]
    calls += [c for run in runs if run.diagnosis for c in run.diagnosis.llm_calls]
    sources = Counter(it.answer_source or "none" for it in iterations)
    n = max(1, len(runs))
    return {
        "runs": len(runs),
        "errors": sum(run.status == "error" for run in runs),
        "questions": len(iterations) / n,
        "stops": Counter(run.stop_reason for run in runs),
        "sources": sources,
        "llm_calls": len(calls) / n,
        "strategy_cost": sum(run.strategy_cost_usd for run in runs),
        "environment_cost": sum(run.environment_cost_usd for run in runs),
        "seconds": sum(run.elapsed_s for run in runs) / n,
    }


def build(record: ExperimentRecord, evaluation: dict[str, Any]) -> str:
    by_strategy: dict[str, Any] = evaluation["by_strategy"]
    facts = {key: run_facts(record, key) for key in by_strategy}
    best = {m: max(s["metrics"][m] for s in by_strategy.values()) for m in SHOWN}
    e = html.escape

    rows = []
    for key, summary in by_strategy.items():
        cells = ""
        for m in SHOWN:
            value = summary["metrics"][m]
            shown = pct(value) if m.startswith("hit") else f"{value:.3f}"
            cells += f'<td class="{"best" if value == best[m] else ""}">{shown}</td>'
        rows.append(f"<tr><td>{e(title(key))}</td>{cells}<td>{summary['case_runs']}</td></tr>")
    results = (
        "<table><tr><th>Strategy</th>"
        + "".join(f"<th>{LABELS.get(m, m.replace('hit_rate', 'Hit rate'))}</th>" for m in SHOWN)
        + "<th>Cases</th></tr>" + "".join(rows) + "</table>"
    )  # fmt: skip

    intervals = "".join(
        f"<tr><td>{e(title(key))}</td>"
        + "".join(
            "<td>{} ({} to {})</td>".format(
                pct(s["metrics"][m]), *(pct(v) for v in wilson(s["metrics"][m], s["case_runs"]))
            )
            for m in ("hit_rate@1", "hit_rate@10")
        )
        + "</tr>"
        for key, s in by_strategy.items()
    )

    def stops(counter: Counter[str]) -> str:
        return ", ".join(f"{name.replace('_', ' ')} {count}" for name, count in counter.items())

    conduct = "".join(
        f"<tr><td>{e(title(key))}</td><td>{f['questions']:.2f}</td><td>{e(stops(f['stops']))}</td>"
        f"<td>{f['llm_calls']:.1f}</td><td>{f['seconds']:.0f}</td>"
        f"<td>${f['strategy_cost']:.2f}</td><td>${f['environment_cost']:.2f}</td>"
        f"<td>{f['errors']}</td><td>{by_strategy[key]['without_differential']}</td></tr>"
        for key, f in facts.items()
    )
    sources = "".join(
        f"<tr><td>{e(title(key))}</td>"
        + "".join(f"<td>{f['sources'].get(s, 0)}</td>"
                  for s in ("case_study", "literature", "unanswerable", "none"))
        + "</tr>"
        for key, f in facts.items()
    )  # fmt: skip
    coding = "".join(
        f"<tr><td>{e(title(key))}</td><td>{s['predictions']}</td><td>{s['predictions_uncoded']}"
        f"</td><td>{s['without_coded_prediction']}</td><td>{s['true_diagnosis_uncoded']}</td></tr>"
        for key, s in by_strategy.items()
    )

    models = sorted({m for s in record.strategies.values() for m in s.get("models", [])})
    overall = record.summary.get("overall", {})
    cost = overall.get("cost_usd", {})
    minutes = (record.elapsed_s or 0) / 60
    took = f"{minutes / 60:.1f} h" if minutes >= 90 else f"{minutes:.0f} min"
    limit = record.config.stopping.max_iterations
    coded = evaluation["coding"]
    reruns = ""
    if record.reruns:
        again = Counter(str(r["strategy"]) for r in record.reruns)
        listed = ", ".join(f"{count} of {title(key)}" for key, count in again.items())
        reruns = (
            f"<li>{len(record.reruns)} case runs failed on a token limit in the first pass and "
            f"were run again ({e(listed)}); the results use the second attempt.</li>"
        )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Information collection strategies: results</title><style>{CSS}</style></head><body>
<h1>Information Collection Strategies Experiment</h1>
<p class="lead">Diagnostic accuracy of five information collection strategies on
{len(record.case_ids)} simulated cases</p>
<p class="note">Run {e(record.started_at)} to {e(record.finished_at or "")} · record
<code>{e(Path(record.output).name)}</code> · status {e(record.status)} · commit
{e(str(record.code_version.get("git_commit", ""))[:7])}</p>

<h2>Result</h2>
{results}
<p class="note">Bold marks the best value in a column. Hit rate@k: share of cases whose true
diagnosis code is among the first k codes of the strategy's differential. nDCG@10 and MRR reward
a true diagnosis placed higher. Every case counts in the denominator.</p>
<figure>{chart(by_strategy)}</figure>

<h2>How sure the differences are</h2>
<table><tr><th>Strategy</th><th>Hit rate@1 (95% interval)</th><th>Hit rate@10 (95% interval)</th>
</tr>{intervals}</table>
<p class="note">Wilson intervals over the cases of this single run. The strategies ran on the
same cases, so the paired comparison below is the sharper test.</p>
{paired(evaluation)}

<h2>What was run</h2>
<ul>
<li>{len(record.case_ids)} cases from <code>{e(record.config.cases_file)}</code>, each run with
every strategy: {len(record.case_runs)} case runs.</li>
<li>Each strategy could ask at most {limit} questions and could stop earlier by its own rule.
When it stopped, it gave a differential of up to 10 diagnoses with probabilities.</li>
<li>Strategy model: {e(", ".join(models))}. Simulated environment model:
{e(str(record.environment_settings.get("default_model")))}; literature sources
{e(", ".join(record.environment_settings.get("enabled_sources", [])))}.</li>
<li>Coding: {e(coded["system"])}, {e(coded["method"])}. A prediction counts as a hit only when
its code equals the true diagnosis code exactly.</li>
{reruns}<li>Total time {took}; total cost ${cost.get("total", 0):.2f}
(strategies ${cost.get("strategy", 0):.2f}, environment ${cost.get("environment", 0):.2f}).</li>
</ul>

<h2>How the strategies behaved</h2>
<table><tr><th>Strategy</th><th>Questions per case</th><th>Why runs stopped</th>
<th>Strategy LLM calls per case</th><th>Seconds per case</th><th>Strategy cost</th>
<th>Environment cost</th><th>Failed runs</th><th>No differential</th></tr>{conduct}</table>
<table><tr><th>Where the answers came from (questions)</th><th>Case study</th><th>Literature</th>
<th>Unanswerable</th><th>No answer (error)</th></tr>{sources}</table>

<h2>Coding</h2>
<table><tr><th>Strategy</th><th>Predicted diagnoses</th><th>Without an ICD code</th>
<th>Cases with no coded prediction</th><th>Cases whose true diagnosis has no code</th></tr>
{coding}</table>
<p class="note">{coded["names"]} distinct diagnosis names were coded; {coded["names_uncoded"]}
have no ICD-11 match. A case whose true diagnosis has no code cannot be hit by any strategy.</p>

<h2>Reading these numbers</h2>
<ul>
<li>Exact code match is strict: a correct diagnosis worded so that the search returns a
neighbouring code (a parent, a sibling, or a code with a different extension) counts as a miss.
</li>
<li>One run per case and strategy. LLM sampling differs between runs, so small differences
between strategies may not repeat.</li>
<li>The stopping thresholds are starting values and were not tuned.</li>
<li>Answers marked "literature" are synthesized by the simulated environment when the case text
is silent; they are plausible, not facts about the patient.</li>
</ul>
</body></html>"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evaluation.report", description=__doc__.splitlines()[0])
    parser.add_argument("record", type=Path)
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args(argv)
    stem = args.record.name.removesuffix(".partial.jsonl").removesuffix(".json")
    evaluation = json.loads(args.record.with_name(f"{stem}.eval.json").read_text("utf-8"))
    page = args.record.with_name(f"{stem}.report.html")
    page.write_text(build(load_record(args.record), evaluation), encoding="utf-8")
    print(f"Wrote {page}", file=sys.stderr)
    if not args.no_pdf:
        pdf = page.with_suffix(".pdf")
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf}", page.resolve().as_uri()],
            check=True, capture_output=True, timeout=120,
        )  # fmt: skip
        print(f"Wrote {pdf}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
