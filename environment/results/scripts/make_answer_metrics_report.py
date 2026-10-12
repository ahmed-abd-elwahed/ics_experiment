"""Build the answer-metrics report (HTML and PDF) from the scored results; no API calls.

Usage: python environment/results/scripts/make_answer_metrics_report.py
Reads environment/results/answer_metrics/answer_metrics.json (make_answer_metrics.py full),
test_run2_haiku.json (make_answer_metrics.py test) and report_facts.json (spend and run
notes), and writes answer_metrics_report.html and .pdf next to them (the PDF is printed from
the HTML by headless Google Chrome).
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SHARED = Path(__file__).resolve().parents[1] / "answer_metrics"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

OLD = ["mc_same", "mc_exact", "fc_consistent"]
NEW = ["zlog", "zlog_sat", "faith", "align_aligned", "align_contra"]
HEAD = {
    "mc_same": "same category (incl. exact)",
    "mc_exact": "exact",
    "fc_consistent": "consistent",
    "zlog": "mean |z| ↓",
    "zlog_sat": "satisfactory",
    "faith": "supported",
    "align_aligned": "aligned",
    "align_contra": "contradicted ↓",
}
GROUPS = [
    ("Masked correctness", ["mc_same", "mc_exact"], "old"),
    ("Factual consistency", ["fc_consistent"], "old"),
    ("Zlog z-score", ["zlog", "zlog_sat"], "new"),
    ("Faithfulness", ["faith"], "new"),
    ("Case alignment", ["align_aligned", "align_contra"], "new"),
]
SHORT = {
    "gemini_knowledge": "Gemini knowledge",
    "current": "EPMC + LitSense, without 1–4",
    "improved_1to4": "EPMC + LitSense, with 1–4",
    "openrouter_exa_instant": "Exa instant",
    "openrouter_parallel_basic": "Parallel basic",
    "openrouter_perplexity": "Perplexity",
}
MODEL_NAMES = {
    "anthropic/claude-haiku-5.5": "Claude Haiku 5.5",
    "z-ai/glm-5.3-flash": "GLM 5.3 Flash",
    "openai/gpt-6-luna": "GPT-6 Luna",
    "typesafe/jev-1.13": "Jev 1.13",
}


def esc(text: Any) -> str:
    return html.escape(str(text))


def value_cell(text: str, n: int, most: int, first: bool) -> str:
    mean, _, sd = text.partition(" ± ")
    shown = esc(mean) + (f'<span class="sd"> ± {esc(sd)}</span>' if sd else "")
    if 1 < n < most:
        shown += f'<span class="n"> ({n})</span>'
    classes = ("first " if first else "") + ("na" if text == "–" else "")
    return f'<td class="{classes.strip()}">{shown}</td>'


def scores_table(data: dict[str, Any], panel_name: str) -> str:
    panel = data["panels"][panel_name]
    most = max(max(v.values()) for v in panel["n_runs"].values())
    top = ['<th rowspan="2" class="cfg">Configuration</th>']
    second = []
    for title, keys, kind in GROUPS:
        top.append(f'<th colspan="{len(keys)}" class="group {kind}">{esc(title)}</th>')
        second += [
            f'<th class="{"first" if i == 0 else ""}">{esc(HEAD[k])}</th>'
            for i, k in enumerate(keys)
        ]
    rows = []
    for config, name in data["order"]:
        cells = [f'<td class="cfg">{esc(name)}</td>']
        for _, keys, _ in GROUPS:
            for i, key in enumerate(keys):
                cells.append(
                    value_cell(
                        panel["cells"][key][config], panel["n_runs"][key][config], most, i == 0
                    )
                )
        row_class = ' class="setc"' if config == "case_information" else ""
        rows.append(f"<tr{row_class}>{''.join(cells)}</tr>")
    return (
        f"<table class='scores'><thead><tr>{''.join(top)}</tr><tr>{''.join(second)}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def fmt(metric: str, value: float | None, digits: int = 2) -> str:
    if value is None:
        return "–"
    percent = metric not in ("zlog", "zlog_v1")
    return f"{value * (100 if percent else 1):.{digits}f}"


def test_table(test: dict[str, Any]) -> str:
    order = [
        ("mc_same", "old"), ("mc_exact", "old"), ("fc_consistent", "old"),
        ("zlog_v1", "first"), ("zlog", "revised, kept"),
        ("zlog_v1_sat", "first"), ("zlog_sat", "revised, kept"),
        ("faith", "kept as designed"),
        ("align_v1_aligned", "first"), ("align_aligned", "revised, kept"),
        ("align_v1_contra", "first"), ("align_contra", "revised, kept"),
    ]  # fmt: skip
    configs = list(SHORT)
    head = "".join(f"<th>{esc(SHORT[c])}</th>" for c in configs)
    rows = []
    for key, version in order:
        result = test["metrics"].get(key)
        if not result:
            continue
        means = "".join(
            f"<td>{fmt(key, result['means'].get(c), 1) if c in result['means'] else '–'}</td>"
            for c in configs
        )
        strong = ' class="strong"' if (result["signal_to_noise"] or 0) >= 2 else ""
        rows.append(
            f"<tr{strong}><td class='cfg'>{esc(test['titles'][key])}</td><td>{esc(version)}</td>"
            f"{means}<td class='first'>{fmt(key, result['spread'])}</td>"
            f"<td>{fmt(key, result['noise'])}</td>"
            f"<td><b>{(result['signal_to_noise'] or 0):.2f}</b></td>"
            f"<td>{result['pairs_separated']} of {result['pairs']}</td></tr>"
        )
    return (
        "<table class='scores small'><thead><tr><th class='cfg'>Metric</th><th>Version</th>"
        f"{head}<th class='first'>Spread</th><th>Noise</th><th>Signal ÷ noise</th>"
        f"<th>Pairs separated</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def sensitivity_table(data: dict[str, Any]) -> str:
    rows = []
    for key in OLD + NEW:
        cells = [f"<td class='cfg'>{esc(data['metrics'][key])}</td>"]
        for panel_name in ("three_judges", "with_jev"):
            s = data["panels"][panel_name]["sensitivity"].get(key)
            if not s:
                cells += ["<td class='first na'>–</td>", *["<td class='na'>–</td>"] * 4]
                continue
            cells += [
                f"<td class='first'>{s['runs']}</td>",
                f"<td>{fmt(key, s['spread'])}</td>",
                f"<td>{fmt(key, s['run_sd'])}</td>",
                f"<td><b>{(s['signal_to_noise'] or 0):.2f}</b></td>",
                f"<td>{s['pairs_separated']} of {s['pairs']}</td>",
            ]
        strong = data["panels"]["three_judges"]["sensitivity"].get(key) or {}
        cls = ' class="strong"' if (strong.get("signal_to_noise") or 0) >= 2 else ""
        rows.append(f"<tr{cls}>{''.join(cells)}</tr>")
    sub = (
        "<th class='first'>Runs</th><th>Spread</th><th>Run SD</th><th>Signal ÷ noise</th>"
        "<th>Pairs separated</th>"
    )
    return (
        "<table class='scores small'><thead><tr><th rowspan='2' class='cfg'>Metric</th>"
        "<th colspan='5' class='group'>Three judges</th>"
        "<th colspan='5' class='group'>With Jev added</th></tr>"
        f"<tr>{sub}{sub}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


STYLE = """
  @page { size: A4 landscape; margin: 12mm 12mm 13mm; }
  body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1b1b1b;
         font-size: 10.5px; line-height: 1.42; }
  h1 { font-size: 21px; margin: 0 0 3px; }
  h2 { font-size: 14.5px; margin: 16px 0 5px; border-bottom: 1.5px solid #8a94a6;
       padding-bottom: 2px; break-after: avoid; }
  h3 { font-size: 11.5px; margin: 10px 0 3px; break-after: avoid; }
  p { margin: 4px 0; } p.sub { color: #555; margin: 0 0 8px; }
  ul, ol { margin: 4px 0; padding-left: 17px; } li { margin: 2px 0; }
  .cols { column-count: 2; column-gap: 22px; }
  .cols > * { break-inside: avoid; }
  ol.cols > li { break-inside: avoid; }
  .box { background: #f4f6fa; border-left: 3px solid #8a94a6; padding: 6px 10px; margin: 6px 0; }
  .eq { font-family: "SF Mono", Menlo, monospace; font-size: 10px; background: #f6f6f6;
        padding: 3px 7px; margin: 3px 0; display: block; }
  table { border-collapse: collapse; width: 100%; margin: 6px 0 4px; break-inside: avoid; }
  th, td { border: 1px solid #cfcfcf; padding: 4px 5px; text-align: center; }
  table.scores thead tr:first-child th { background: #e9eef6; font-size: 10.5px; }
  table.scores thead tr:nth-child(2) th { background: #f4f6fa; font-weight: 600; }
  th.group, th.first, td.first { border-left: 2px solid #8a94a6; }
  th.new { background: #e3f0e6 !important; }
  td.cfg, th.cfg { text-align: left; } td.cfg { font-weight: 600; }
  table.scores td { white-space: nowrap; } table.scores td.cfg { white-space: normal; }
  table.small { font-size: 9.5px; } table.plain td { text-align: left; vertical-align: top; }
  table.plain th { background: #f4f6fa; text-align: left; }
  span.sd { color: #666; } span.n { color: #a05a00; font-size: 8.5px; } td.na { color: #999; }
  tbody tr:nth-child(even) td { background-color: #fafafa; }
  tr.setc td { border-top: 2px solid #8a94a6; }
  tr.strong td { background-color: #eaf5ec !important; }
  .note { color: #444; font-size: 9.5px; } .break { break-before: page; }
"""


def build(data: dict[str, Any], test: dict[str, Any], facts: dict[str, Any]) -> str:
    panel3 = ", ".join(MODEL_NAMES.get(m, m) for m in data["panels"]["three_judges"]["panel"])
    body = facts["sections"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>New answer metrics for the simulated environment</title>
<style>{STYLE}</style></head><body>
<h1>New answer metrics for the simulated environment</h1>
<p class="sub">Information Collection Strategies Experiment · environment benchmark ·
{esc(facts["date"])}</p>
{body["summary"]}
<h2>Final scores: three judges</h2>
<p class="note">Panel: {esc(panel3)}; the label is the majority vote, the zlog score the median of
the judges. Mean <span class="sd">± SD</span> over runs. Green headers are the new metrics. ↓ lower
is better. {esc(facts["runs_note"])}</p>
{scores_table(data, "three_judges")}
<div class="break"></div>
<h2>Final scores: the same table with the Jev decision model added as a fourth judge</h2>
<p class="note">{esc(facts["jev_note"])}</p>
{scores_table(data, "with_jev")}
{body["reading"]}
<div class="break"></div>
{body["why"]}
{body["metrics"]}
<div class="break"></div>
<h2>Development: the test on one run with one judge</h2>
{body["test_intro"]}
{test_table(test)}
{body["test_outcome"]}
<div class="break"></div>
<h2>Sensitivity over all judged runs</h2>
{body["sensitivity_intro"]}
{sensitivity_table(data)}
{body["judges"]}
{body["limits"]}
</body></html>
"""


def main() -> None:
    data = json.loads((SHARED / "answer_metrics.json").read_text(encoding="utf-8"))
    test = json.loads((SHARED / "test_run2_haiku.json").read_text(encoding="utf-8"))
    facts = json.loads((SHARED / "report_facts.json").read_text(encoding="utf-8"))
    page = SHARED / "answer_metrics_report.html"
    page.write_text(build(data, test, facts), encoding="utf-8")
    pdf = SHARED / "answer_metrics_report.pdf"
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", page.as_uri()],
        check=True, capture_output=True,
    )  # fmt: skip
    print(f"Wrote {pdf}", file=sys.stderr)


if __name__ == "__main__":
    main()
