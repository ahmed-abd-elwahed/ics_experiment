"""Accuracy against cost: one line per strategy through its runs at several question budgets.

    .venv/bin/python -m evaluation.plot_cost OUT_STEM "4=a.eval.json" "8=b.eval.json" ... [--k K]

x = the run's total cost in US dollars (strategy and environment calls, all case runs of the
strategy), y = top-k accuracy in % (default k = 10). Each run is a star marker; each strategy
is a line through its runs in budget order, which a note under the legend states. Writes
OUT_STEM.svg, OUT_STEM.html (with the values as a table), OUT_STEM.pdf, OUT_STEM.png and OUT_STEM.json. No API calls.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import subprocess
from collections.abc import Sequence
from pathlib import Path

from evaluation.plot_complexity import COLOURS
from evaluation.plot_topk import CHROME, GRID, INK, MUTED, SURFACE, TITLES

AXIS = "#c3c2b7"


def star(cx: float, cy: float, r: float) -> str:
    """A five-pointed star centred on (cx, cy), outer radius r."""
    points = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        points.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(points)


def nice_step(span: float) -> float:
    raw = span / 5
    base = 10 ** math.floor(math.log10(raw))
    return next(m * base for m in (1, 2, 2.5, 5, 10) if m * base >= raw)


def figure(series: dict[str, list[tuple[str, float, float]]], k: int) -> str:
    width, height = 1000, 600
    left, right, top, bottom = 64, 150, 56, 56
    pw, ph = width - left - right, height - top - bottom
    xs = [c for pts in series.values() for _, c, _ in pts]
    ys = [v for pts in series.values() for _, _, v in pts]
    x_step = nice_step(max(xs))
    x_max = math.ceil(max(xs) * 1.05 / x_step) * x_step
    y_lo = math.floor((min(ys) - 2) / 5) * 5
    y_hi = math.ceil((max(ys) + 2) / 5) * 5

    def x(c: float) -> float:
        return left + c / x_max * pw

    def y(v: float) -> float:
        return top + ph - (v - y_lo) / (y_hi - y_lo) * ph

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" font-family="-apple-system, Helvetica Neue, '
           f'Arial, sans-serif" role="img" aria-label="Top-{k} accuracy against cost for '
           f'each strategy">',
           f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>']  # fmt: skip
    lx = float(left)
    for s in series:  # legend, in strategy order
        out.append(f'<polygon points="{star(lx + 6, 20, 7)}" fill="{COLOURS[s]}"/>'
                   f'<text x="{lx + 18}" y="24" font-size="12" fill="{INK}">'
                   f'{html.escape(TITLES[s])}</text>')  # fmt: skip
        lx += 18 + 7.2 * len(TITLES[s]) + 26
    budgets = ", ".join(label for label, _, _ in next(iter(series.values())))
    out.append(f'<text x="{left}" y="44" font-size="11" fill="{MUTED}">Stars along each line, '
               f'left to right: {html.escape(budgets)} questions.</text>')  # fmt: skip
    for tick in range(int(y_lo), int(y_hi) + 1, 5):
        out.append(f'<line x1="{left}" x2="{left + pw}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/><text x="{left - 8}" '
                   f'y="{y(tick) + 4:.1f}" font-size="11" text-anchor="end" '
                   f'fill="{MUTED}">{tick}%</text>')  # fmt: skip
    tick = 0.0
    while tick <= x_max + 1e-9:
        out.append(f'<line x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{top + ph}" '
                   f'y2="{top + ph + 5}" stroke="{AXIS}" stroke-width="1"/><text '
                   f'x="{x(tick):.1f}" y="{top + ph + 20}" font-size="11" text-anchor="middle" '
                   f'fill="{MUTED}">${tick:.2f}</text>')  # fmt: skip
        tick += x_step
    out.append(f'<line x1="{left}" x2="{left}" y1="{top}" y2="{top + ph}" stroke="{AXIS}" '
               f'stroke-width="1"/><line x1="{left}" x2="{left + pw}" y1="{top + ph}" '
               f'y2="{top + ph}" stroke="{AXIS}" stroke-width="1"/>')  # fmt: skip
    out.append(f'<text x="{left + pw / 2}" y="{height - 10}" font-size="12" text-anchor="middle" '
               f'fill="{MUTED}">Cost (US$, all 272 cases)</text>'
               f'<text transform="translate(18 {top + ph / 2}) rotate(-90)" font-size="12" '
               f'text-anchor="middle" fill="{MUTED}">Top-{k} accuracy</text>')  # fmt: skip

    ends = []
    for s, pts in series.items():
        line = " ".join(f"{x(c):.1f},{y(v):.1f}" for _, c, v in pts)
        out.append(
            f'<polyline points="{line}" fill="none" stroke="{COLOURS[s]}" '
            'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for label, c, v in pts:
            tip = f"{TITLES[s]}, {label} questions: top-{k} {v:.1f}%, ${c:.2f}"
            out.append(f'<g><title>{html.escape(tip)}</title>'
                       f'<circle cx="{x(c):.1f}" cy="{y(v):.1f}" r="12" fill="transparent"/>'
                       f'<polygon points="{star(x(c), y(v), 9)}" fill="{COLOURS[s]}" '
                       f'stroke="{SURFACE}" stroke-width="2" stroke-linejoin="round"/>'
                       "</g>")  # fmt: skip
        _, c, v = pts[-1]
        ends.append([y(v), x(c), TITLES[s].split(". ", 1)[-1], s])
    placed = -math.inf
    for end in sorted(ends):  # direct labels right of each line's last star, pushed apart
        at = max(end[0] + 4, placed + 15)
        placed = at
        out.append(f'<text x="{end[1] + 16:.1f}" y="{at:.1f}" font-size="12" '
                   f'fill="{INK}">{html.escape(end[2])}</text>')  # fmt: skip
    return "".join(out) + "</svg>"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stem", type=Path)
    parser.add_argument("runs", nargs="+", metavar="LABEL=EVAL_JSON", help="in budget order")
    parser.add_argument("--k", type=int, default=10, help="top-k accuracy (default 10)")
    parser.add_argument("--title", default="")
    args = parser.parse_args(argv)

    specs = [(label, Path(path)) for label, _, path in (r.partition("=") for r in args.runs)]
    evals = [(label, json.loads(path.read_text(encoding="utf-8"))) for label, path in specs]
    series = {
        s: [(label, e["by_strategy"][s]["cost_usd"],
             100 * e["by_strategy"][s]["metrics"][f"hit_rate@{args.k}"]) for label, e in evals]
        for s in TITLES if all(s in e["by_strategy"] for _, e in evals)
    }  # fmt: skip
    svg = figure(series, args.k)
    stem = args.stem
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".svg").write_text(svg, encoding="utf-8")
    stem.with_suffix(".json").write_text(json.dumps(
        {"k": args.k, "runs": [{"label": label, "evaluation": str(path)} for label, path in specs],
         "by_strategy": {s: [{"questions": lbl, "cost_usd": c, f"top{args.k}_pct": v}
                             for lbl, c, v in pts] for s, pts in series.items()}},
        indent=2) + "\n", encoding="utf-8")  # fmt: skip
    rows = "".join(
        f"<tr><td>{html.escape(TITLES[s])}</td><td>{lbl}</td><td>${c:.2f}</td>"
        f"<td>{v:.1f}%</td></tr>"
        for s, pts in series.items()
        for lbl, c, v in pts
    )
    title = args.title or f"Top-{args.k} accuracy against cost"
    page = stem.with_suffix(".html")
    page.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Accuracy and cost</title>
<style>@page {{ size: A4 landscape; margin: 10mm; }}
body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: {INK};
background: {SURFACE}; margin: 0; }} h1 {{ font-size: 18px; margin: 0 0 4px; }}
p {{ font-size: 12px; color: {MUTED}; margin: 0 0 8px; }}
table {{ border-collapse: collapse; font-size: 11px; margin-top: 10px; break-before: page; }}
th, td {{ border-bottom: 1px solid {GRID}; padding: 4px 8px; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
td {{ font-variant-numeric: tabular-nums; }}</style></head><body>
<h1>{html.escape(title)}</h1>
<p>{html.escape(", ".join(f"{label} questions: {path.name}" for label, path in specs))}. Cost:
strategy and environment calls over all 272 case runs. Top {args.k}: the true diagnosis's
ICD-11 code is among the strategy's first {args.k} diagnoses (exact code match).</p>
{svg}<table><thead><tr><th>Strategy</th><th>Questions</th><th>Cost</th><th>Top {args.k}</th>
</tr></thead><tbody>{rows}</tbody></table></body></html>""",
        encoding="utf-8",
    )
    for flag, out in (("--print-to-pdf", stem.with_suffix(".pdf")),
                      ("--screenshot", stem.with_suffix(".png"))):  # fmt: skip
        extra = ["--window-size=1000,600", "--hide-scrollbars"] if flag == "--screenshot" else []
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
