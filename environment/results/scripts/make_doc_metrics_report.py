"""Build the document-metrics report (HTML and PDF) from the scored results; no API calls.

Usage: PYTHONPATH=.:environment python environment/results/scripts/make_doc_metrics_report.py
Reads environment/results/doc_metrics/scores.json (``python -m bench.doc_metrics score``) and
the stored records for cost and time, and writes doc_metrics_report.html and .pdf next to it
(the PDF is printed from the HTML by headless Google Chrome).
"""

# ruff: noqa: E501  (the HTML template keeps its lines as written)
from __future__ import annotations

import html
import json
import os
import statistics
import subprocess
import sys
from typing import Any

from bench.answer_metrics import MetricJudgment
from bench.doc_metrics import (
    CHANGES,
    WORKSPACE,
    DocJudgment,
    DocWorkspace,
    FrozenQuery,
    faithfulness_file,
)
from bench.schemas import RunRecord, calls_cost
from bench.workspace import read_models

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCORES = WORKSPACE / "scores.json"

STYLE = """
  @page { size: A4; margin: 13mm 12mm 14mm; }
  body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1b1b1b;
         font-size: 10.5px; line-height: 1.45; }
  h1 { font-size: 21px; margin: 0 0 3px; }
  h2 { font-size: 14.5px; margin: 16px 0 5px; border-bottom: 1.5px solid #8a94a6;
       padding-bottom: 2px; break-after: avoid; }
  p { margin: 4px 0; } p.sub { color: #555; margin: 0 0 8px; }
  ul { margin: 4px 0; padding-left: 17px; } li { margin: 2px 0; }
  .box { background: #f4f6fa; border-left: 3px solid #8a94a6; padding: 6px 10px; margin: 6px 0; }
  table { border-collapse: collapse; width: 100%; margin: 6px 0 4px; break-inside: avoid; }
  th, td { border: 1px solid #cfcfcf; padding: 3px 5px; text-align: center; }
  th { background: #e9eef6; } td.cfg, th.cfg { text-align: left; }
  td { white-space: nowrap; } td.cfg { white-space: normal; }
  tbody tr:nth-child(even) td { background-color: #fafafa; }
  tr.win td { background-color: #eaf5ec !important; font-weight: 600; }
  tr.base td { background-color: #f1f3f7 !important; }
  span.ci { color: #666; font-size: 9px; } .pos { color: #1d6b32; } .neg { color: #a12a1a; }
  .note { color: #444; font-size: 9.5px; }
"""


def esc(text: Any) -> str:
    return html.escape(str(text))


def pct(v: float) -> str:
    return f"{100 * v:.1f}%"


def ci(pair: list[float] | tuple[float, float], scale: float = 100.0, fmt: str = ".1f") -> str:
    return f'<span class="ci">({scale * pair[0]:{fmt}} to {scale * pair[1]:{fmt}})</span>'


def delta(d: dict[str, Any] | None, scale: float = 100.0, fmt: str = "+.1f") -> str:
    if not d:
        return ""
    low, high = d["ci"]
    cls = "pos" if low > 0 else "neg" if high < 0 else ""
    return (f'<span class="{cls}">{scale * d["mean"]:{fmt}}</span> '
            f'<span class="ci">({scale * low:{fmt}} to {scale * high:{fmt}})</span>')  # fmt: skip


def label(name: str) -> str:
    if name.startswith("stored_run"):
        run, _, config = name.removeprefix("stored_run").partition("_")
        return f"stored run {int(run)}: {config}"
    return name


def describe(name: str, entry: dict[str, Any]) -> str:
    return esc(entry.get("description", ""))


def costs() -> dict[str, float]:
    ws = DocWorkspace()
    queries = sum(calls_cost(q.llm_calls) for q in read_models(ws.queries, FrozenQuery))
    retrieval = sum(
        r.retrieval_cost_usd
        for f in os.listdir(ws.root / "runs")
        for r in read_models(ws.root / "runs" / f, RunRecord)
    )
    judge = sum(calls_cost(j.llm_calls) for j in read_models(ws.judgments, DocJudgment))
    judge += sum(
        calls_cost(r.llm_calls) for r in read_models(faithfulness_file(ws), MetricJudgment)
    )
    answers = sum(
        sum(r.llm_cost_usd.values())
        for f in os.listdir(ws.root / "answers")
        for r in read_models(ws.root / "answers" / f, RunRecord)
    )
    return {"queries": queries, "retrieval": retrieval, "judge": judge, "answers": answers,
            "total": queries + retrieval + judge + answers}  # fmt: skip


def row(name: str, e: dict[str, Any], cls: str = "") -> str:
    vs = e.get("vs_baseline", {})
    return (
        f'<tr class="{cls}"><td class="cfg"><b>{esc(label(name))}</b><br>'
        f'<span class="note">{describe(name, e)}</span></td>'
        f"<td>{pct(e['strict'])}</td><td>{delta(vs.get('strict'))}</td>"
        f"<td>{pct(e['category'])}</td><td>{e['ndcg']:.3f}</td>"
        f"<td>{delta(vs.get('ndcg'), 1.0, '+.3f')}</td><td>{pct(e['precision'])}</td>"
        f"<td>{e['questions']}</td></tr>"
    )


HEAD = (
    "<tr><th class='cfg'>Configuration</th><th>Strict coverage</th><th>Δ strict vs baseline "
    "(95% CI)</th><th>Category coverage</th><th>nDCG@8</th><th>Δ nDCG vs baseline</th>"
    "<th>Precision@8</th><th>n</th></tr>"
)


def faithfulness_section(scores: dict[str, Any], winner: str) -> str:
    """Faithfulness of the answers medsim writes on each configuration's documents."""
    f = scores.get("faithfulness") or {}
    if "baseline" not in f or winner not in f:
        return ""
    cells = ("covered_supported", "covered_not_supported", "not_covered_supported",
             "not_covered_not_supported")  # fmt: skip
    rows = ""
    for name in ("baseline", winner):
        e = f[name]
        d = e.get("vs_baseline")
        rows += (
            f'<tr class="{"win" if name == winner else "base"}"><td class="cfg"><b>{esc(name)}</b></td>'
            f"<td>{pct(e['supported'])} {ci(e['supported_ci'])}</td><td>{delta(d)}</td>"
            + "".join(f"<td>{e['by_coverage'].get(c, 0)}</td>" for c in cells)
            + "</tr>"
        )
    return f"""<h2>Faithfulness of the answers written on these documents</h2>
<p>medsim's answer-writing stage (Stage C) was run on each configuration's documents, with the
frozen queries, and every answer with documents was judged for faithfulness with the benchmark's
rubric (<code>bench.answer_metrics</code>): does at least one document give a value for this variable
in a comparable patient that agrees with the answer? Same judge; a question with no answer counts as
not supported.</p>
<table><thead><tr><th class="cfg">Configuration</th><th>Supported (95% CI)</th>
<th>Δ vs baseline (paired)</th><th>Covered and supported</th><th>Covered, not supported</th>
<th>Not covered, supported</th><th>Neither</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">"Covered" is strict truth coverage of the same documents. Covered but not supported
means the documents held a value matching the truth but the answer was not backed by them: the
answer-writing stage, not retrieval, is where those questions are lost. This judge reads "agrees"
strictly (in one example, 9.8 cm in the document against 9.6 cm in the answer was not supported).</p>"""


def build(scores: dict[str, Any], winner: str, spend: dict[str, float]) -> str:
    c: dict[str, Any] = scores["configs"]
    base = c["baseline"]
    singles = sorted(
        (n for n in c if n in CHANGES),
        key=lambda n: (-c[n]["strict"], -c[n]["ndcg"]),
    )
    combos = sorted((n for n in c if "+" in n and "@" not in n),
                    key=lambda n: (-c[n]["strict"], -c[n]["ndcg"]))  # fmt: skip
    stored = sorted(n for n in c if n.startswith("stored_run") and n.endswith("improved_1to4"))
    stored_strict = [c[n]["strict"] for n in stored]
    stored_ndcg = [c[n]["ndcg"] for n in stored]
    fresh = [n for n in c if "@" in n]
    shuffled = c.get("baseline (shuffled)")
    again = c.get("baseline#2")
    w = c[winner]
    judge_noise = abs(again["strict"] - base["strict"]) if again else 0.0

    def table(names: list[str]) -> str:
        rows = "".join(
            row(n, c[n], "win" if n == winner else "base" if n == "baseline" else "") for n in names
        )
        return f"<table><thead>{HEAD}</thead><tbody>{rows}</tbody></table>"

    fresh_rows = ""
    for qs in sorted({n.split("@")[1] for n in fresh}):
        for cfg in ("baseline", winner):
            name = f"{cfg}@{qs}"
            if name in c:
                fresh_rows += row(name, c[name], "win" if cfg == winner else "base")
    fresh_table = (f"<table><thead>{HEAD}</thead><tbody>{fresh_rows}</tbody></table>"
                   if fresh_rows else "<p>Not run.</p>")  # fmt: skip
    fresh_note = ""
    pairs = []
    for qs in sorted({n.split("@")[1] for n in fresh}):
        a, b = c.get(f"baseline@{qs}"), c.get(f"{winner}@{qs}")
        if a and b:
            pairs.append((qs, b["strict"] - a["strict"], b["ndcg"] - a["ndcg"]))
    if pairs:
        fresh_note = "; ".join(
            f"query set {qs}: strict {100 * ds:+.1f} points, nDCG {dn:+.3f}" for qs, ds, dn in pairs
        )

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Retrieved-document metrics</title><style>{STYLE}</style></head><body>
<h1>Which retrieval settings find the true value?</h1>
<p class="sub">Truth coverage and graded relevance of the documents medsim retrieves (Europe PMC +
LitSense), on the 141 set A questions of the retrieval benchmark · judge {esc(scores["judge_model"])}
· {len(c)} scored configurations and controls</p>

<div class="box"><b>Result.</b> The best configuration is <b>{esc(winner)}</b>
({esc(c[winner]["description"])}): strict truth coverage {pct(w["strict"])} against the
baseline's {pct(base["strict"])} ({delta(w.get("vs_baseline", {}).get("strict"))} points,
paired over the same questions), nDCG@8 {w["ndcg"]:.3f} against {base["ndcg"]:.3f}, and precision@8
{pct(w["precision"])} against {pct(base["precision"])}.
{("On fresh queries: " + esc(fresh_note) + ".") if fresh_note else ""}</div>

<h2>What was measured</h2>
<ul>
<li><b>Strict truth coverage</b> (decides): a document gives a value or range for this variable
in patients with this or a closely related condition, and the hidden true value lies inside it or
within about 15%. <b>Category coverage</b> (shown): a document's value, range, or level, a
reference range for comparable patients included, puts the true value in the same low / normal /
high category.</li>
<li><b>Graded relevance</b>: each document 0 (not about the variable or the condition), 1 (about
them, no usable value), or 2 (a value for the variable in comparable patients).
<b>nDCG@8</b> is against a perfect list of eight grade-2 documents, so it rewards better documents
and a better order (it breaks ties); <b>precision@8</b> is the share of grade-2 documents.</li>
<li>One judge call per question grades all eight documents and gives both coverage verdicts. Every
positive verdict needs a verbatim quote that code finds in the named document; an unverified grade 2
counts as 1, and unverified coverage as not covered.</li>
<li>Each configuration retrieves for the same <b>frozen search query</b> per question (medsim's
Stages A and B once, with the stored runs' model {esc("deepseek/deepseek-v4-flash-0731")}), and no
answer is written. Differences between configurations therefore come from the retrieval settings.
Eight documents per question throughout. Search results are cached, so a configuration that issues
the same requests gets the same results.</li>
</ul>

<h2>Can the metrics be trusted?</h2>
<table><thead><tr><th class="cfg">Check</th><th>Strict coverage</th><th>Category</th><th>nDCG@8</th>
<th class="cfg">Reading</th></tr></thead><tbody>
<tr><td class="cfg">Shuffled control: each question judged on another question's documents</td>
<td>{pct(shuffled["strict"]) if shuffled else "–"}</td><td>{pct(shuffled["category"]) if shuffled else "–"}</td>
<td>{f"{shuffled['ndcg']:.3f}" if shuffled else "–"}</td>
<td class="cfg">Near zero: the judge reads the documents rather than answering from the question.</td></tr>
<tr><td class="cfg">The baseline's documents judged twice</td><td>{pct(base["strict"])} / {pct(again["strict"]) if again else "–"}</td>
<td>{pct(base["category"])} / {pct(again["category"]) if again else "–"}</td>
<td>{base["ndcg"]:.3f} / {f"{again['ndcg']:.3f}" if again else "–"}</td>
<td class="cfg">The judge's own noise: {100 * judge_noise:.1f} points of strict coverage.</td></tr>
<tr><td class="cfg">Stored benchmark runs 2–{len(stored) + 1} of the baseline method (fresh queries, full pipeline)</td>
<td>{pct(statistics.fmean(stored_strict))} ± {100 * statistics.stdev(stored_strict):.1f}</td><td>–</td>
<td>{statistics.fmean(stored_ndcg):.3f} ± {statistics.stdev(stored_ndcg):.3f}</td>
<td class="cfg">Run-to-run spread (mean ± SD) when the query is written anew; the frozen-query
baseline ({pct(base["strict"])}) lies inside it.</td></tr>
<tr><td class="cfg">Stored run 2 of the original retrieval (<code>current</code>)</td>
<td>{pct(c["stored_run02_current"]["strict"])}</td><td>{pct(c["stored_run02_current"]["category"])}</td>
<td>{c["stored_run02_current"]["ndcg"]:.3f}</td>
<td class="cfg">About 20 points below changes 1–4: the metrics separate a known difference.</td></tr>
</tbody></table>

<h2>Single changes from the baseline</h2>
<p>The baseline is medsim's default retrieval (changes 1–4: value-first ranking in one list,
50 Europe PMC candidates, animal and age filter, article-body search with excerpts, value-based
broadening). Each row changes one setting. Differences are paired over the same 141 questions,
with 95% bootstrap intervals; green intervals exclude zero.</p>
{table(["baseline", *singles])}
<p class="note">With 21 changes tested at 95%, about one could look better or worse by chance alone;
treat single changes whose interval only just excludes zero with care.</p>

<h2>Combinations</h2>
<p>The changes with the largest positive estimates, added to the best single change.</p>
{table(["baseline", *combos]) if combos else "<p>Not run.</p>"}

<h2>Confirmation on fresh queries</h2>
<p>The baseline and the best configuration again, each on two new sets of queries written by the
same query builder: the gain should hold when the queries change. Here each Δ compares with the
baseline on the same query set.</p>
{fresh_table}

{faithfulness_section(scores, winner)}

<h2>Cost and limits</h2>
<ul>
<li>Cost of this work from the stored usage records: ${spend["total"]:.2f} (judge ${spend["judge"]:.2f},
LLM selection during retrieval ${spend["retrieval"]:.2f}, query writing ${spend["queries"]:.2f}).
Europe PMC and LitSense are free.</li>
<li>One judge, an LLM, without human labels: absolute levels may be off; the comparisons between
configurations, made by the same judge on the same questions, are the point.</li>
<li>141 questions: differences of a few points are inside the noise.</li>
<li>Europe PMC answered HTTP 503 during the first retrieval of the two fresh-query baseline runs (129 and 64 of
141 questions lost it). Those questions were retrieved again once it recovered and judged again; the tables use
the second attempt. Every other run had no failed source.</li>
<li>LLM selection adds one call per question to medsim's retrieval (about $0.0016 with
deepseek/deepseek-v4-flash-0731, and its latency). It is not medsim's default yet.</li>
<li>The best configuration was chosen on these questions; the fresh-query runs re-test it, but on
the same 141 questions, not on new ones.</li>
</ul>
</body></html>"""


def main() -> int:
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    winner = sys.argv[1] if len(sys.argv) > 1 else "llm_select20"
    page = WORKSPACE / "doc_metrics_report.html"
    page.write_text(build(scores, winner, costs()), encoding="utf-8")
    pdf = page.with_suffix(".pdf")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", page.as_uri()],
        check=True, capture_output=True, timeout=120,
    )  # fmt: skip
    print(f"Wrote {page} and {pdf}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
