# ruff: noqa: RUF001  (en dashes in score ranges are intended)
"""Bar chart of each strategy's accuracy per INTERMED complexity bucket.

    .venv/bin/python -m evaluation.plot_complexity OUT_STEM SCORES_JSON CUTS \
        --run "4 questions=a.eval.json" [--run "8 questions=b.eval.json" ...] [--k K]

CUTS are the lower bounds of every bucket after the first, comma-separated: "12,16,21,27"
gives 0-11, 12-15, 16-20, 21-26, 27-60. One group of bars per bucket (x), one bar per strategy,
y = top-k accuracy in % (default k = 1). With one run, each bar has its 95% Wilson interval.
With several runs (in budget order), the first run's bar is in the strategy's colour, in front;
each later run is a bar from zero to its accuracy behind it, in one colour shared by every
strategy (dark gray, then light gray), so where it is higher it shows on top and each colour
ends at its run's accuracy. A later run at or below an earlier one is hidden behind it and is
drawn as a tick across the bar at its accuracy. The intervals of every run are in the table.
Writes OUT_STEM.svg,
OUT_STEM.html (with the values as a table), OUT_STEM.pdf and OUT_STEM.png (printed by headless
Google Chrome, like plot_topk). No API calls.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import subprocess
from collections.abc import Sequence
from itertools import pairwise
from pathlib import Path
from typing import Any

from evaluation.plot_topk import CHROME, GRID, INK, MUTED, SURFACE, TITLES

# The dataviz reference palette's first four categorical slots, in fixed order; validated
# (adjacent pairs, light surface): worst CVD dE 9.1, normal-vision 22.9. Aqua and yellow are
# under 3:1 on the surface, so the figure ships with its table.
COLOURS = {"hypothesis": "#2a78d6", "knowledge": "#eb6834", "channel": "#1baf7a",
           "sequence": "#eda100"}  # fmt: skip
# With several runs, the first run keeps the strategy colours; the later runs share one colour
# each across strategies: dark gray, then light gray. Each validated next to every strategy
# colour on the light surface (worst CVD dE 18.3, normal-vision >= 21.8); they fail only the
# chroma floor, as neutrals should. Light gray is under 3:1, so the figure carries its table.
LATER_COLOURS = ("#52514e", "#b5b3ac")
MAX_SCORE = 60


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def bucket_labels(cuts: list[int]) -> list[str]:
    bounds = [0, *cuts, MAX_SCORE + 1]
    return [f"{lo}–{hi - 1}" for lo, hi in pairwise(bounds)]


def hit(run: dict[str, Any], k: int) -> bool:
    """The evaluation's own rule (evaluation.metrics): the true code's rank is at most k."""
    rank = run.get("rank")
    return rank is not None and rank <= k


SCORE_METRICS = {"mrr": "MRR", "ndcg@10": "nDCG@10"}


def tabulate(evaluation: dict[str, Any], scores: dict[str, int], cuts: list[int], k: int,
             metric: str | None = None,
             ) -> tuple[list[str], dict[str, list[dict[str, float]]], list[int]]:  # fmt: skip
    """Per strategy and bucket: top-k accuracy, or with `metric` ("mrr", "ndcg@10") the mean of
    the evaluation's per-case score. `pct` is always on a 0-100 scale (a score times 100)."""
    labels = bucket_labels(cuts)
    strategies = [s for s in TITLES if s in evaluation["by_strategy"]]
    counts = {s: [[0, 0] for _ in labels] for s in strategies}
    for run in evaluation["case_runs"]:
        if run["strategy"] not in counts:
            continue
        b = sum(scores[run["case_id"]] >= c for c in cuts)
        counts[run["strategy"]][b][0] += run["scores"][metric] if metric else hit(run, k)
        counts[run["strategy"]][b][1] += 1
    cases = [sum(scores[c] >= lo for lo in cuts) for c in scores]
    sizes = [cases.count(i) for i in range(len(labels))]
    if metric:
        table = {s: [{"sum": h, "n": n, "pct": 100 * h / n if n else 0.0, "value": h / n if n
                      else 0.0} for h, n in counts[s]] for s in strategies}  # fmt: skip
        return labels, table, sizes
    table = {
        s: [{"hits": h, "n": n, "pct": 100 * h / n if n else 0.0,
             "lo": 100 * wilson(h, n)[0], "hi": 100 * wilson(h, n)[1]} for h, n in counts[s]]
        for s in strategies
    }  # fmt: skip
    return labels, table, sizes


def bar_path(x0: float, w: float, top_y: float, base: float) -> str:
    """A bar with 4px rounded top corners, square on the baseline."""
    r = min(4.0, w / 2, base - top_y)
    return (f"M{x0:.1f},{base:.1f} V{top_y + r:.1f} Q{x0:.1f},{top_y:.1f} {x0 + r:.1f},"
            f"{top_y:.1f} H{x0 + w - r:.1f} Q{x0 + w:.1f},{top_y:.1f} {x0 + w:.1f},"
            f"{top_y + r:.1f} V{base:.1f} Z")  # fmt: skip


def figure(labels: list[str], runs: list[tuple[str, dict[str, list[dict[str, float]]]]],
           sizes: list[int], k: int, intervals: bool = True,
           metric: str | None = None) -> str:  # fmt: skip
    strategies = list(runs[0][1])
    single = len(runs) == 1
    whiskers = single and intervals and not metric
    y_name = SCORE_METRICS[metric] if metric else f"Top-{k} accuracy"

    def y_tick(t: int) -> str:
        return f"{t / 100:.1f}" if metric else f"{t}%"

    def shown(c: dict[str, float]) -> str:
        if metric:
            return f"{c['value']:.3f}"
        return f"{c['pct']:.1f}% ({c['hits']}/{c['n']})"

    width, height = 1000, 520
    left, right, top, bottom = 56, 20, 64, 64
    pw, ph = width - left - right, height - top - bottom
    peak = max(c["hi" if whiskers else "pct"] for _, t in runs for v in t.values() for c in v)
    y_max = max(10.0, math.ceil(peak / 10) * 10)
    group_w = pw / len(labels)
    bar_w = min(36.0, (group_w * 0.72 - 2 * (len(strategies) - 1)) / len(strategies))
    span = len(strategies) * bar_w + 2 * (len(strategies) - 1)

    def y(v: float) -> float:
        return top + ph - v / y_max * ph

    def colour(s: str, j: int) -> str:
        return COLOURS[s] if j == 0 else LATER_COLOURS[j - 1]

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" font-family="-apple-system, Helvetica Neue, '
           f'Arial, sans-serif" role="img" aria-label="{y_name} of each strategy by '
           f'INTERMED complexity bucket">',
           f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>']  # fmt: skip
    legend = [(COLOURS[s], TITLES[s]) for s in strategies]
    legend += [(LATER_COLOURS[j - 1], label) for j, (label, _) in enumerate(runs) if j]
    lx = float(left)
    for n, (fill, text) in enumerate(legend):
        if n == len(strategies):  # the later runs, after a divider
            out.append(f'<line x1="{lx - 12}" x2="{lx - 12}" y1="12" y2="28" stroke="{GRID}" '
                       f'stroke-width="1"/>')  # fmt: skip
            lx += 8
        out.append(f'<rect x="{lx}" y="14" width="12" height="12" rx="2" fill="{fill}"/>'
                   f'<text x="{lx + 18}" y="24" font-size="12" fill="{INK}">'
                   f'{html.escape(text)}</text>')  # fmt: skip
        lx += 18 + 7.2 * len(text) + 26
    if not single:
        out.append(
            f'<text x="{left}" y="46" font-size="11" fill="{MUTED}">Strategy colour: '
            f"{html.escape(runs[0][0])}. Gray bars rise to the later runs' accuracy; a "
            f"gray tick marks a later run that scored lower or the same.</text>"
        )
    for tick in range(0, int(y_max) + 1, 10):
        out.append(f'<line x1="{left}" x2="{left + pw}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/><text x="{left - 6}" '
                   f'y="{y(tick) + 4:.1f}" font-size="11" text-anchor="end" '
                   f'fill="{MUTED}">{y_tick(tick)}</text>')  # fmt: skip
    out.append(f'<text transform="translate(14 {top + ph / 2}) rotate(-90)" font-size="11" '
               f'text-anchor="middle" fill="{MUTED}">{y_name}</text>')  # fmt: skip
    base = y(0)
    for g, label in enumerate(labels):
        gx = left + g * group_w + (group_w - span) / 2
        out.append(f'<text x="{left + (g + 0.5) * group_w:.1f}" y="{top + ph + 20}" '
                   f'font-size="12" font-weight="600" text-anchor="middle" fill="{INK}">'
                   f'{label}</text><text x="{left + (g + 0.5) * group_w:.1f}" '
                   f'y="{top + ph + 36}" font-size="11" text-anchor="middle" fill="{MUTED}">'
                   f'{sizes[g]} cases</text>')  # fmt: skip
        for i, s in enumerate(strategies):
            x0 = gx + i * (bar_w + 2)
            cells = [(j, rl, t[s][g]) for j, (rl, t) in enumerate(runs)]
            tip = f"{TITLES[s]}, score {label}: " + "; ".join(
                f"{rl} {shown(c)}" for _, rl, c in cells
            )
            parts = [f"<g><title>{html.escape(tip)}</title>"]
            # Later runs behind, tallest at the back; the first run always in front.
            order = sorted(cells[1:], key=lambda jc: (-jc[2]["pct"], -jc[0])) + cells[:1]
            ticks = []
            for n, (j, _, c) in enumerate(order):
                front = max((d["pct"] for _, _, d in order[n + 1 :]), default=-1.0)
                if j and c["pct"] <= front:  # hidden behind a bar in front: a tick instead
                    ticks.append((j, c["pct"]))
                    continue
                parts.append(f'<path d="{bar_path(x0, bar_w, y(c["pct"]), base)}" '
                             f'fill="{colour(s, j)}"/>')  # fmt: skip
                if n:  # 2px surface gap where a shorter bar ends in front of a taller one
                    parts.append(f'<line x1="{x0:.1f}" x2="{x0 + bar_w:.1f}" '
                                 f'y1="{y(c["pct"]) - 1:.1f}" y2="{y(c["pct"]) - 1:.1f}" '
                                 f'stroke="{SURFACE}" stroke-width="2"/>')  # fmt: skip
            for j, pct in ticks:  # surface ring, then the run's colour
                ty = y(pct)
                parts.append(f'<line x1="{x0 - 3:.1f}" x2="{x0 + bar_w + 3:.1f}" y1="{ty:.1f}" '
                             f'y2="{ty:.1f}" stroke="{SURFACE}" stroke-width="5"/>'
                             f'<line x1="{x0 - 3:.1f}" x2="{x0 + bar_w + 3:.1f}" y1="{ty:.1f}" '
                             f'y2="{ty:.1f}" stroke="{LATER_COLOURS[j - 1]}" stroke-width="3" '
                             f'stroke-linecap="round"/>')  # fmt: skip
            if whiskers:
                c, cx = cells[0][2], x0 + bar_w / 2
                parts.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(c["lo"]):.1f}" '
                             f'y2="{y(c["hi"]):.1f}" stroke="{INK}" stroke-width="1.2" '
                             f'stroke-opacity="0.55"/>'
                             f'<line x1="{cx - 4:.1f}" x2="{cx + 4:.1f}" y1="{y(c["hi"]):.1f}" '
                             f'y2="{y(c["hi"]):.1f}" stroke="{INK}" stroke-width="1.2" '
                             f'stroke-opacity="0.55"/>')  # fmt: skip
            out.append("".join(parts) + "</g>")
    out.append(f'<line x1="{left}" x2="{left + pw}" y1="{base:.1f}" y2="{base:.1f}" '
               f'stroke="{MUTED}" stroke-width="1"/>')  # fmt: skip
    out.append(
        f'<text x="{left + pw / 2}" y="{height - 6}" font-size="11" '
        f'text-anchor="middle" fill="{MUTED}">INTERMED complexity score (0–60)</text>'
    )
    return "".join(out) + "</svg>"


def table_html(labels: list[str], runs: list[tuple[str, dict[str, list[dict[str, float]]]]],
               sizes: list[int], metric: str | None = None) -> str:  # fmt: skip
    def cell(c: dict[str, float]) -> str:
        if metric:
            return f"<td>{c['value']:.3f}</td>"
        return f"<td>{c['pct']:.1f}% <span>({c['lo']:.0f}–{c['hi']:.0f})</span></td>"

    head = "".join(f"<th>{lbl}<br><span>{n} cases</span></th>"
                   for lbl, n in zip(labels, sizes, strict=True))  # fmt: skip
    body = "".join(
        f"<tr><td>{html.escape(TITLES[s])}</td><td>{html.escape(rl)}</td>"
        + "".join(cell(c) for c in table[s])
        + "</tr>"
        for s in runs[0][1]
        for rl, table in runs
    )
    return (f"<table><thead><tr><th>Strategy</th><th>Run</th>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table>")  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stem", type=Path)
    parser.add_argument(
        "scores", type=Path, help="an INTERMED scores file (scripts/intermed_scores.py)"
    )
    parser.add_argument("cuts", help='lower bounds of the later buckets, e.g. "12,16,21,27"')
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        metavar="LABEL=EVAL_JSON",
        help="an evaluation, repeated in budget order (at most three)",
    )
    parser.add_argument("--k", type=int, default=1, help="top-k accuracy (default 1)")
    parser.add_argument(
        "--metric",
        choices=list(SCORE_METRICS),
        help="plot this per-case score (mean per bucket) instead of top-k",
    )
    parser.add_argument("--title", default="")
    parser.add_argument(
        "--no-intervals",
        action="store_true",
        help="leave the 95%% interval whiskers off (they stay in the table)",
    )
    args = parser.parse_args(argv)

    if len(args.run) > 3:
        parser.error("at most three runs")
    specs = [(label, Path(path)) for label, _, path in (r.partition("=") for r in args.run)]
    scores = {r["case_id"]: r["intermed_score"]
              for r in json.loads(args.scores.read_text(encoding="utf-8"))["scores"]}  # fmt: skip
    cuts = [int(c) for c in args.cuts.split(",")]
    runs, labels, sizes = [], [], []
    for label, path in specs:
        evaluation = json.loads(path.read_text(encoding="utf-8"))
        labels, table, sizes = tabulate(evaluation, scores, cuts, args.k, args.metric)
        runs.append((label, table))
    svg = figure(labels, runs, sizes, args.k, intervals=not args.no_intervals, metric=args.metric)
    stem = args.stem
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".svg").write_text(svg, encoding="utf-8")
    stem.with_suffix(".json").write_text(json.dumps(
        {"scores": str(args.scores), "cuts": cuts, "k": args.k, "metric": args.metric,
         "buckets": labels,
         "cases_per_bucket": sizes,
         "runs": [{"label": label, "evaluation": str(path), "by_strategy": table}
                  for (label, path), (_, table) in zip(specs, runs, strict=True)]},
        indent=2) + "\n", encoding="utf-8")  # fmt: skip
    y_name = SCORE_METRICS[args.metric] if args.metric else f"Top-{args.k} accuracy"
    title = args.title or f"{y_name} by INTERMED complexity, {len(labels)} buckets"
    if args.metric:
        note = {
            "mrr": "MRR: the mean over the bucket's case runs of 1/rank of the true ICD-11 code "
            "in the strategy's differential (0 when absent).",
            "ndcg@10": "nDCG@10: the mean over the bucket's case runs of 1/log2(rank + 1) of the "
            "true ICD-11 code within the first ten (0 otherwise). With one correct code per "
            "case the ideal DCG is 1, so this is also DCG@10.",
        }[args.metric]
    else:
        note = (
            f"Top {args.k}: the true diagnosis's ICD-11 code is among the strategy's first "
            f"{args.k} diagnoses (exact code match). Brackets"
            + (" and whiskers" if len(runs) == 1 and not args.no_intervals else "")
            + ": 95% Wilson interval."
        )
    page = stem.with_suffix(".html")
    page.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Accuracy by complexity</title>
<style>@page {{ size: A4 landscape; margin: 10mm; }}
body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: {INK};
background: {SURFACE}; margin: 0; }} h1 {{ font-size: 18px; margin: 0 0 4px; }}
p {{ font-size: 12px; color: {MUTED}; margin: 0 0 8px; }}
table {{ border-collapse: collapse; font-size: 11px; margin-top: 10px; }}
th, td {{ border-bottom: 1px solid {GRID}; padding: 4px 8px; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }} span {{ color: {MUTED}; font-weight: 400; }}
td {{ font-variant-numeric: tabular-nums; }}</style></head><body>
<h1>{html.escape(title)}</h1>
<p>{html.escape(", ".join(f"{label}: {path.name}" for label, path in specs))}.
{html.escape(note)}</p>
{svg}{table_html(labels, runs, sizes, args.metric)}</body></html>""",
        encoding="utf-8",
    )
    for flag, out in (("--print-to-pdf", stem.with_suffix(".pdf")),
                      ("--screenshot", stem.with_suffix(".png"))):  # fmt: skip
        extra = ["--window-size=1000,520", "--hide-scrollbars"] if flag == "--screenshot" else []
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", *extra,
             f"{flag}={out}", stem.with_suffix(".svg").resolve().as_uri()
             if flag == "--screenshot" else page.resolve().as_uri()],
            check=True, capture_output=True, timeout=120,
        )  # fmt: skip
    print(f"Wrote {stem}.svg/.html/.pdf/.png/.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
