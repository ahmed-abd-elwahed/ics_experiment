"""Plot top-k accuracy (hit rate at k = 1..10) of each strategy for several runs.

    .venv/bin/python -m evaluation.plot_topk OUT_STEM "4 iterations=a.eval.json" ...
    .venv/bin/python -m evaluation.plot_topk OUT_STEM "4 iterations=r1.eval.json,r2.eval.json"

One panel per strategy, one line per budget (an ordered one-hue ramp: light = fewest iterations),
x = k, y = top@k in %. With several comma-separated evaluations (repeated runs) for a budget,
the line is their mean and a band of the same colour shows ±1 sample standard deviation.
Writes OUT_STEM.svg, OUT_STEM.html (with the values as a table) and OUT_STEM.pdf and
OUT_STEM.png (printed from the HTML by headless Google Chrome). No API calls.

    .venv/bin/python -m evaluation.plot_topk --split OUT_STEM "4 iterations=..." ...

writes one vector plot per strategy instead: OUT_STEM_<strategy>.svg and a .pdf of the same
size, all on the same y axis.
"""

from __future__ import annotations

import html
import json
import math
import re
import statistics
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Ordinal blue ramps by number of budgets, validated (--ordinal): monotone lightness, light end
# 2.06:1. Three budgets: steps 250, 450, 650; four: steps 250, 400, 550, 700.
RAMPS = {
    1: ("#2a78d6",),
    2: ("#86b6ef", "#104281"),
    3: ("#86b6ef", "#2a78d6", "#104281"),
    4: ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b"),
}


def ramp(n: int) -> tuple[str, ...]:
    if n not in RAMPS:
        raise SystemExit(f"plot_topk draws 1 to {max(RAMPS)} budgets, got {n}")
    return RAMPS[n]


INK, MUTED, GRID, SURFACE = "#1f1f1e", "#5e5d59", "#e4e3df", "#fcfcfb"
TITLES = {
    "hypothesis": "1. Hypothesis-driven",
    "knowledge": "2. Knowledge-driven",
    "channel": "3. Channel-based",
    "sequence": "4. Sequence-based",
}
KS = range(1, 11)


Run = tuple[str, list[dict[str, Any]]]  # a budget's label and its repeated evaluations


def load(spec: str) -> Run:
    label, _, paths = spec.partition("=")
    return label, [json.loads(Path(p).read_text(encoding="utf-8")) for p in paths.split(",")]


def one_run(evaluation: dict[str, Any], strategy: str) -> list[float]:
    metrics = evaluation["by_strategy"][strategy]["metrics"]
    return [100 * metrics[f"hit_rate@{k}"] for k in KS]


def values(evaluations: list[dict[str, Any]], strategy: str) -> list[float]:
    """Mean top@k over the repeated runs."""
    per_run = [one_run(e, strategy) for e in evaluations]
    return [statistics.mean(col) for col in zip(*per_run, strict=True)]


def spread(evaluations: list[dict[str, Any]], strategy: str) -> list[float]:
    """Sample standard deviation of top@k over the runs (0 for a single run)."""
    if len(evaluations) < 2:
        return [0.0] * len(KS)
    per_run = [one_run(e, strategy) for e in evaluations]
    return [statistics.stdev(col) for col in zip(*per_run, strict=True)]


def panel(x0: float, y0: float, w: float, h: float, title: str,
          series: list[tuple[str, list[float], list[float], str]],
          y_max: float) -> str:  # fmt: skip
    left, bottom, top, right = 46, 34, 30, 132
    pw, ph = w - left - right, h - top - bottom

    def x(k: int) -> float:
        return x0 + left + (k - 1) * pw / 9

    def y(v: float) -> float:
        return y0 + top + ph - v / y_max * ph

    out = [f'<text x="{x0 + left}" y="{y0 + 18}" font-size="14" font-weight="600" '
           f'fill="{INK}">{html.escape(title)}</text>']  # fmt: skip
    for tick in range(0, int(y_max) + 1, 10):
        out.append(f'<line x1="{x0 + left}" x2="{x0 + left + pw}" y1="{y(tick):.1f}" '
                   f'y2="{y(tick):.1f}" stroke="{GRID}" stroke-width="1"/>')  # fmt: skip
        out.append(f'<text x="{x0 + left - 6}" y="{y(tick) + 4:.1f}" font-size="11" '
                   f'text-anchor="end" fill="{MUTED}">{tick}%</text>')  # fmt: skip
    for k in KS:
        out.append(f'<text x="{x(k):.1f}" y="{y0 + top + ph + 16}" font-size="11" '
                   f'text-anchor="middle" fill="{MUTED}">{k}</text>')  # fmt: skip
    out.append(f'<text x="{x0 + left + pw / 2}" y="{y0 + h - 2}" font-size="11" '
               f'text-anchor="middle" fill="{MUTED}">top k</text>')  # fmt: skip
    ends: list[tuple[float, int, str, str]] = []
    for _, vals, sds, colour in series:  # bands first, so every line stays on top
        if any(sds):
            rows = list(zip(KS, vals, sds, strict=True))
            upper = [f"{x(k):.1f},{y(min(v + d, y_max)):.1f}" for k, v, d in rows]
            lower = [f"{x(k):.1f},{y(max(v - d, 0)):.1f}" for k, v, d in rows]
            out.append(f'<polygon points="{" ".join(upper + lower[::-1])}" fill="{colour}" '
                       'fill-opacity="0.2" stroke="none"/>')  # fmt: skip
    for label, vals, _, colour in series:
        points = " ".join(f"{x(k):.1f},{y(v):.1f}" for k, v in zip(KS, vals, strict=True))
        out.append(f'<polyline points="{points}" fill="none" stroke="{colour}" '
                   'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')  # fmt: skip
        out += [
            f'<circle cx="{x(k):.1f}" cy="{y(v):.1f}" r="4" fill="{colour}" '
            f'stroke="{SURFACE}" stroke-width="2"/>'
            for k, v in zip(KS, vals, strict=True)
        ]
        ends.append((y(vals[-1]), -len(ends), f"{label}: {vals[-1]:.1f}%", colour))
    placed = -math.inf
    for at, _, text, colour in sorted(ends):  # direct labels at the right end, pushed apart
        placed = max(at, placed + 14)
        out.append(f'<circle cx="{x0 + left + pw + 10}" cy="{placed - 4:.1f}" r="4" '
                   f'fill="{colour}"/>')  # fmt: skip
        out.append(f'<text x="{x0 + left + pw + 18}" y="{placed:.1f}" font-size="11" '
                   f'fill="{INK}">{html.escape(text)}</text>')  # fmt: skip
    return "".join(out)


def available(runs: list[Run]) -> list[str]:
    return [s for s in TITLES if all(s in e["by_strategy"] for _, es in runs for e in es)]


def figure(runs: list[Run], only: str | None = None) -> str:
    """All strategies in a 2-column grid, or with ``only`` that strategy's panel alone (legend
    stacked above it). The y axis is the same either way, so split panels stay comparable."""
    strategies = available(runs)
    top = max(v + d for _, es in runs for s in strategies
              for v, d in zip(values(es, s), spread(es, s), strict=True))  # fmt: skip
    y_max = max(10.0, math.ceil(top / 10) * 10)
    if only is not None:
        strategies = [only]
    w, h = 500, 300
    cols = min(2, len(strategies))
    rows = math.ceil(len(strategies) / cols)
    stacked = only is not None
    width = cols * w
    repeated = any(len(es) > 1 for _, es in runs)

    def legend_label(name: str, es: list[dict[str, Any]]) -> str:
        if not repeated:
            return name
        return f"{name} (mean of {len(es)} runs ± SD)" if len(es) > 1 else f"{name} (1 run)"

    labels = [legend_label(name, es) for name, es in runs]
    slots, lx, ly = [], 46.0, 18  # (x, y) of each legend entry; wraps when a row is full
    for label in labels:
        step = 30 + 8 * len(label) + 28
        if not stacked and lx > 46 and lx + 30 + 6.5 * len(label) > width - 10:
            lx, ly = 46.0, ly + 18
        slots.append((lx, ly))
        if stacked:
            ly += 18
        else:
            lx += step
    legend_h = slots[-1][1] + (12 if stacked else 18)
    height = rows * h + legend_h
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'width="{width}" height="{height}" font-family="-apple-system, Helvetica Neue, '
             f'Arial, sans-serif" role="img" aria-label="Top-k accuracy by strategy for '
             f'{len(runs)} iteration budgets">',
             f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>']  # fmt: skip
    colours = ramp(len(runs))
    for label, (lx, ly), colour in zip(labels, slots, colours, strict=True):  # legend
        parts.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{ly}" y2="{ly}" stroke="{colour}" '
                     f'stroke-width="2"/><circle cx="{lx + 11}" cy="{ly}" r="4" fill="{colour}" '
                     f'stroke="{SURFACE}" stroke-width="2"/><text x="{lx + 30}" y="{ly + 4}" '
                     f'font-size="12" fill="{INK}">{html.escape(label)}</text>')  # fmt: skip
    for i, strategy in enumerate(strategies):
        series = [(label, values(es, strategy), spread(es, strategy), colour)
                  for (label, es), colour in zip(runs, colours, strict=True)]  # fmt: skip
        parts.append(panel((i % cols) * w, legend_h + (i // cols) * h, w, h,
                           TITLES[strategy], series, y_max))  # fmt: skip
    return "".join(parts) + "</svg>"


def table(runs: list[Run]) -> str:
    head = "".join(f"<th>top {k}</th>" for k in KS)
    body = ""
    for strategy, title in TITLES.items():
        for label, es in runs:
            if all(strategy in e["by_strategy"] for e in es):
                sds = spread(es, strategy) if len(es) > 1 else None
                cells = "".join(
                    f"<td>{v:.1f}" + (f" ± {sds[i]:.1f}" if sds else "") + "</td>"
                    for i, v in enumerate(values(es, strategy))
                )
                body += (
                    f"<tr><td>{html.escape(title)}</td><td>{html.escape(label)}</td>{cells}</tr>"
                )
    return (f"<table><thead><tr><th>Strategy</th><th>Run</th>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table>")  # fmt: skip


def repeats_note(runs: list[Run]) -> str:
    counts = [len(es) for _, es in runs]
    if max(counts) < 2:
        return ""
    each = ", ".join(f"{html.escape(label)}: {len(es)}" for label, es in runs)
    return (
        f" Lines are the mean of repeated runs ({each}); the shaded band is ±1 sample "
        "standard deviation across them."
    )


def write_vector(svg: str, stem: Path) -> None:
    """``stem.svg`` and a ``stem.pdf`` of exactly the figure's size (vector, printed by
    headless Chrome from a one-page HTML wrapper that is deleted afterwards)."""
    stem.with_suffix(".svg").write_text(svg, encoding="utf-8")
    width, height = re.search(r'width="(\d+)" height="(\d+)"', svg).groups()  # type: ignore[union-attr]
    page = stem.with_name(stem.name + ".print.html")
    page.write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><style>@page {{ size: {width}px '
        f"{height}px; margin: 0; }} html, body {{ margin: 0; }} svg {{ display: block; }}"
        f"</style></head><body>{svg}</body></html>",
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={stem.with_suffix('.pdf')}", page.resolve().as_uri()],
            check=True, capture_output=True, timeout=120,
        )  # fmt: skip
    finally:
        page.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    split = bool(args) and args[0] == "--split"
    if split:
        args = args[1:]
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    stem, runs = Path(args[0]), [load(spec) for spec in args[1:]]
    if split:
        for strategy in available(runs):
            write_vector(figure(runs, only=strategy), stem.with_name(f"{stem.name}_{strategy}"))
        print(f"Wrote {stem}_<strategy>.svg/.pdf for {', '.join(available(runs))}",
              file=sys.stderr)  # fmt: skip
        return 0
    svg = figure(runs)
    stem.with_suffix(".svg").write_text(svg, encoding="utf-8")
    page = stem.with_suffix(".html")
    page.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Top-k accuracy</title>
<style>@page {{ size: A4 landscape; margin: 10mm; }}
body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: {INK};
background: {SURFACE}; margin: 0; }} h1 {{ font-size: 18px; margin: 0 0 4px; }}
p {{ font-size: 12px; color: {MUTED}; margin: 0 0 8px; }}
table {{ border-collapse: collapse; font-size: 10px; margin-top: 10px; break-before: page; }}
th, td {{ border-bottom: 1px solid {GRID}; padding: 3px 6px; text-align: right; }}
th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
td {{ font-variant-numeric: tabular-nums; }}</style></head><body>
<h1>Top-k accuracy by number of iterations</h1>
<p>272 cases per strategy and run. Top k: the true diagnosis's ICD-11 code is among the
strategy's first k diagnoses (exact code match).{repeats_note(runs)}</p>
{svg}{table(runs)}</body></html>""",
        encoding="utf-8",
    )
    for flag, out in (("--print-to-pdf", stem.with_suffix(".pdf")),
                      ("--screenshot", stem.with_suffix(".png"))):  # fmt: skip
        extra = ["--window-size=1000,660", "--hide-scrollbars"] if flag == "--screenshot" else []
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", *extra,
             f"{flag}={out}", stem.with_suffix(".svg").resolve().as_uri()
             if flag == "--screenshot" else page.resolve().as_uri()],
            check=True, capture_output=True, timeout=120,
        )  # fmt: skip
    print(f"Wrote {stem}.svg/.html/.pdf/.png", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
