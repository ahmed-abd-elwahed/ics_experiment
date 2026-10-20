# ruff: noqa: E501  (the HTML template keeps its lines as written)
"""One table of every search method, its benchmark results and its cost; no API calls.

Usage: PYTHONPATH=.:environment python environment/results/scripts/make_search_methods_table.py
Reads the repeated benchmark (repeats/repeat_summary.json, answer_metrics/answer_metrics.json,
the stored runs for retrieval cost), the 50-question study of retrieval changes 1-6 (its figures
are copied from results/README.md, 2026-09-21), and the document-metric search
(doc_metrics/scores.json and its runs). Writes search_methods/search_methods.html, .md and .pdf
(the PDF is printed from the HTML by headless Google Chrome).
"""

from __future__ import annotations

import html
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

from bench.doc_metrics import CHANGES, DocWorkspace, config_runs
from bench.schemas import RunRecord
from bench.workspace import latest_by, read_models

RESULTS = Path(__file__).resolve().parents[1]
OUT = RESULTS / "search_methods"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
QUESTIONS_AB = 413  # sets A and B of the benchmark
QUESTIONS_C = 272

NAMES = {
    "gemini_knowledge": (
        "Gemini 3 Flash knowledge",
        "no search: the model states the typical value",
    ),
    "current": ("Europe PMC + LitSense, original", "the retrieval as first built (no changes 1–4)"),
    "improved_1to4": ("Europe PMC + LitSense, changes 1–4", "medsim's current default"),
    "openrouter_exa_instant": ("Exa (instant)", "OpenRouter web search, medical domains"),
    "openrouter_parallel_basic": ("Parallel (basic)", "OpenRouter web search, medical domains"),
    "openrouter_perplexity": ("Perplexity", "OpenRouter web search, medical domains"),
    "openrouter_google": ("Native Google search", "Gemini 3.1 Flash Lite's own search (one run)"),
    "openrouter_openai": ("Native OpenAI search", "GPT-6 Luna's own search (one run)"),
    "case_information": ("Case only (reference)", "no retrieval; set C questions the case answers"),
}
# Where the stored runs keep retrieval cost: run 2 for the repeated methods, run 1 for the two
# native searches (run once).
RETRIEVAL_RUN = {"openrouter_google": 1, "openrouter_openai": 1}

# The 50-question study (results/README.md, 2026-09-21): earlier metrics, one judge, one run.
STUDY = [
    (
        "Current (original)",
        "Europe PMC + LitSense as first evaluated",
        45,
        22,
        44,
        84,
        0.00000,
        0.00108,
        87,
    ),
    (
        "Current + Europe PMC fix",
        "malformed Europe PMC replies retried",
        50,
        38,
        47,
        81,
        0.00000,
        0.00100,
        79,
    ),
    (
        "Changes 1–4",
        "value-first ranking, animal and age filter, excerpts, new fallbacks",
        63,
        53,
        59,
        81,
        0.00000,
        0.00093,
        96,
    ),
    (
        "Changes 1–5",
        "plus natural-language LitSense queries",
        62,
        50,
        38,
        78,
        0.00000,
        0.00089,
        102,
    ),
    (
        "Changes 1–6",
        "plus an LLM that picks the 8 documents",
        59,
        47,
        47,
        78,
        0.00091,
        0.00178,
        196,
    ),
    (
        "OpenRouter search",
        "Exa web search tool, 8 results, medical domains",
        35,
        41,
        53,
        81,
        0.00669,
        0.00750,
        83,
    ),
    (
        "OpenRouter search, improved",
        "the same with changes 1–3 applied",
        48,
        47,
        56,
        78,
        0.00685,
        0.00754,
        83,
    ),
]


def esc(text: Any) -> str:
    return html.escape(str(text))


def mean_sd(values: list[float], unit: str = "%", digits: int = 1) -> str:
    if not values:
        return "–"
    m = statistics.fmean(values)
    if len(values) == 1:
        return f"{m:.{digits}f}{unit}"
    return f"{m:.{digits}f} ± {statistics.stdev(values):.{digits}f}{unit}"


def benchmark_rows() -> list[dict[str, Any]]:
    summary = json.loads((RESULTS / "repeats" / "repeat_summary.json").read_text("utf-8"))[
        "configs"
    ]
    metrics = json.loads((RESULTS / "answer_metrics" / "answer_metrics.json").read_text("utf-8"))
    cells = metrics["panels"]["three_judges"]["cells"]
    rows = []
    for key, (name, what) in NAMES.items():
        runs = summary[key]["runs"]
        # After run 1 OpenRouter raised the DeepSeek output price; the repeated methods' cost is
        # the mean of runs 2 and later (as in repeat_summary.md), the native searches' run 1's.
        later = [r["total_cost_usd"] for n, r in runs.items() if int(n) >= 2] or [
            r["total_cost_usd"] for r in runs.values()
        ]
        n_questions = QUESTIONS_C if key == "case_information" else QUESTIONS_AB
        retrieval = None
        if key != "case_information":
            ws_run = RETRIEVAL_RUN.get(key, 2)
            folder = RESULTS / ("retriever_comparison" if ws_run == 1 else "repeats/run_02/sets_ab")
            recs = latest_by(
                read_models(folder / "runs" / f"{key}.jsonl", RunRecord), lambda r: r.item_id
            )
            ok = [r for r in recs.values() if r.status == "ok"]
            retrieval = statistics.fmean(r.retrieval_cost_usd for r in ok) if ok else None
        coverage = ndcg = None
        if key in ("current", "improved_1to4"):
            scores = json.loads((RESULTS / "doc_metrics" / "scores.json").read_text("utf-8"))[
                "configs"
            ]
            entry = scores.get(f"stored_run02_{key}")
            if entry:
                coverage, ndcg = entry["strict"], entry["ndcg"]
        rows.append({
            "key": key, "name": name, "what": what, "runs": len(runs),
            "mc_same": cells["mc_same"][key], "mc_exact": cells["mc_exact"][key],
            "fc": cells["fc_consistent"][key], "zlog": cells["zlog"][key],
            "zlog_sat": cells["zlog_sat"][key], "faith": cells["faith"][key],
            "aligned": cells["align_aligned"][key],
            "run_cost": statistics.fmean(later), "per_question": statistics.fmean(later) / n_questions,
            "retrieval": retrieval,
            "time": mean_sd([r["mean_time_s"] for r in runs.values()], " s", 0),
            "coverage": coverage, "ndcg": ndcg, "ndcg_s": "–" if ndcg is None else f"{ndcg:.3f}",
        })  # fmt: skip
    return rows


def doc_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scores = json.loads((RESULTS / "doc_metrics" / "scores.json").read_text("utf-8"))
    ws = DocWorkspace()
    rows = []
    for name, entry in scores["configs"].items():
        if name.startswith("stored") or "shuffled" in name or "#" in name or "@" in name:
            continue
        runs = config_runs(ws, name)
        cost = statistics.fmean(r.retrieval_cost_usd for r in runs.values()) if runs else 0.0
        parts = [] if name == "baseline" else name.split("+")
        rows.append({
            "name": name, "kind": "baseline" if not parts else "single" if len(parts) == 1 else "combination",
            "what": "medsim's default (changes 1–4)" if not parts else "; ".join(CHANGES[p].description for p in parts),
            "strict": entry["strict"], "category": entry["category"], "ndcg": entry["ndcg"],
            "precision": entry["precision"], "vs": entry.get("vs_baseline", {}), "retrieval": cost,
        })  # fmt: skip
    rows.sort(key=lambda r: (-r["strict"], -r["ndcg"]))
    return rows, scores


def pct(v: float | None) -> str:
    return "–" if v is None else f"{100 * v:.1f}%"


def delta(d: dict[str, Any] | None, scale: float = 100, fmt: str = "+.1f") -> str:
    if not d:
        return ""
    low, high = d["ci"]
    cls = "pos" if low > 0 else "neg" if high < 0 else ""
    return f'<span class="{cls}">{scale * d["mean"]:{fmt}}</span> <span class="ci">({scale * low:{fmt}} to {scale * high:{fmt}})</span>'


def money(v: float | None, digits: int = 4) -> str:
    return "–" if v is None else f"${v:.{digits}f}"


STYLE = """
@page { size: A4 landscape; margin: 10mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1b1b1b; font-size: 9.5px; line-height: 1.38; }
h1 { font-size: 19px; margin: 0 0 2px; } h2 { font-size: 13px; margin: 14px 0 4px; border-bottom: 1.5px solid #8a94a6; padding-bottom: 2px; break-after: avoid; }
p { margin: 3px 0; } .sub { color: #555; } .note { color: #444; font-size: 8.8px; }
table { border-collapse: collapse; width: 100%; margin: 4px 0; }
th, td { border: 1px solid #d0d3d9; padding: 3px 4px; text-align: right; vertical-align: top; }
th { background: #e9eef6; font-weight: 600; text-align: center; } td.l, th.l { text-align: left; }
td { font-variant-numeric: tabular-nums; } tbody tr:nth-child(even) td { background: #fafafa; }
tr.base td { background: #f1f3f7 !important; } tr.win td { background: #eaf5ec !important; font-weight: 600; }
tr.group td { background: #f4f6fa !important; font-weight: 600; text-align: left; }
.what { color: #555; font-size: 8.6px; font-weight: 400; display: block; }
.pos { color: #1d6b32; } .neg { color: #a12a1a; } .ci { color: #777; font-size: 8.2px; }
"""


def build() -> tuple[str, str]:
    bench = benchmark_rows()
    docs, scores = doc_rows()
    faith = scores.get("faithfulness", {})
    winner = docs[0]["name"]

    b_rows = "".join(
        f'<tr class="{"base" if r["key"] == "improved_1to4" else ""}"><td class="l"><b>{esc(r["name"])}</b>'
        f'<span class="what">{esc(r["what"])}</span></td><td>{r["runs"]}</td>'
        f"<td>{esc(r['mc_same'])}</td><td>{esc(r['mc_exact'])}</td><td>{esc(r['fc'])}</td>"
        f"<td>{esc(r['zlog'])}</td><td>{esc(r['zlog_sat'])}</td><td>{esc(r['faith'])}</td>"
        f"<td>{esc(r['aligned'])}</td><td>{pct(r['coverage'])}</td>"
        f"<td>{r['ndcg_s']}</td>"
        f"<td>{money(r['retrieval'])}</td><td>{money(r['per_question'])}</td>"
        f"<td>${r['run_cost']:.2f}</td><td>{esc(r['time'])}</td></tr>"
        for r in bench
    )
    s_rows = "".join(
        f'<tr><td class="l"><b>{esc(n)}</b><span class="what">{esc(w)}</span></td>'
        f"<td>{rel}%</td><td>{truth}%</td><td>{close}%</td><td>{cat}%</td>"
        f"<td>{money(ret, 5)}</td><td>{money(tot, 5)}</td><td>{t} s</td></tr>"
        for n, w, rel, truth, close, cat, ret, tot, t in STUDY
    )

    def doc_row(r: dict[str, Any]) -> str:
        cls = "win" if r["name"] == winner else "base" if r["kind"] == "baseline" else ""
        f = faith.get(r["name"])
        faith_cell = f"{pct(f['supported'])}" if f else "–"
        return (
            f'<tr class="{cls}"><td class="l"><b>{esc(r["name"])}</b><span class="what">{esc(r["what"])}</span></td>'
            f"<td>{pct(r['strict'])}</td><td>{delta(r['vs'].get('strict'))}</td><td>{pct(r['category'])}</td>"
            f"<td>{r['ndcg']:.3f}</td><td>{delta(r['vs'].get('ndcg'), 1, '+.3f')}</td>"
            f"<td>{pct(r['precision'])}</td><td>{faith_cell}</td><td>{money(r['retrieval'])}</td></tr>"
        )

    groups = [
        ("Baseline", "baseline"),
        ("Combinations", "combination"),
        ("Single changes", "single"),
    ]
    d_rows = ""
    for title, kind in groups:
        d_rows += f'<tr class="group"><td colspan="9">{title}</td></tr>'
        d_rows += "".join(doc_row(r) for r in docs if r["kind"] == kind)

    w = next(r for r in docs if r["name"] == winner)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Search methods</title><style>{STYLE}</style></head><body>
<h1>Search methods: benchmark results and cost</h1>
<p class="sub">Every search method the simulated environment was tested with, and every optimization tried on its
original Europe PMC + LitSense retrieval. Three studies, with different questions and metrics, so each has its own table.</p>

<h2>1. The search methods on the repeated benchmark</h2>
<p>413 questions per run (set A: 141 with a hidden true value; set B: 272 never stated), up to 10 runs, scored by a
three-judge panel (Claude Haiku 5.5, GLM 5.3 Flash, GPT-6 Luna). Mean ± SD over runs. Every method uses medsim's
stages on DeepSeek V4 Flash; only the retrieval differs. The shaded row is medsim's current default.</p>
<table><thead><tr><th class="l">Search method</th><th>Runs</th><th>Masked correctness: same category</th><th>Masked correctness: exact</th>
<th>Factual consistency</th><th>Zlog mean |z| ↓</th><th>Zlog satisfactory</th><th>Faithfulness: supported</th>
<th>Case alignment: aligned</th><th>Strict truth coverage*</th><th>nDCG@8*</th><th>Retrieval cost / question</th>
<th>Total cost / question</th><th>Cost / run</th><th>Time / answer</th></tr></thead><tbody>{b_rows}</tbody></table>
<p class="note">* Document metrics (section 3's definitions) on stored run 2's documents, measured only for Europe PMC + LitSense.
Retrieval cost: search fees and search or selection model tokens (Europe PMC and LitSense are free). Total cost includes
medsim's three LLM stages. Cost per run is the mean of runs 2 and later (OpenRouter raised the DeepSeek price after run 1);
the native searches ran once. Case only answers 272 set C questions and scores near 100% by construction: it is a ceiling,
not a search method.</p>

<h2>2. Earlier optimizations of the original retrieval (50-question study, 2026-09-21)</h2>
<p>One run of 50 questions with the earlier metrics, before the repeated benchmark: the changes 1–6 to Europe PMC + LitSense
and the first OpenRouter web search. Changes 1–4 became medsim's default.</p>
<table><thead><tr><th class="l">Method</th><th>Relevant documents (grade ≥ 2)</th><th>Questions with a document containing the true value</th>
<th>Final answer close to the true value</th><th>Final answer in the true category</th><th>Retrieval cost / question</th>
<th>Total cost / question</th><th>Time / question</th></tr></thead><tbody>{s_rows}</tbody></table>
<p class="note">Figures from results/README.md (2026-09-21). Quality is on the 44 questions where every method retrieved (32 with a hidden value).</p>

<h2>3. The document-metric search on Europe PMC + LitSense (2026-10-16)</h2>
<p>141 set A questions, one frozen search query per question, retrieval only, one judge (Claude Haiku 5.5). Strict truth
coverage decides: a document gives a value for patients like this one and the true value lies in its range or within
about 15%. Δ is paired against the baseline over the same questions, with 95% bootstrap intervals (green: excludes zero).
Faithfulness (answers written on these documents and judged by the same judge) was measured for the baseline and the winner.
Best: <b>{esc(winner)}</b>, strict coverage {pct(w["strict"])} against {pct(next(r for r in docs if r["kind"] == "baseline")["strict"])}.</p>
<table><thead><tr><th class="l">Configuration</th><th>Strict truth coverage</th><th>Δ vs baseline</th><th>Category coverage</th>
<th>nDCG@8</th><th>Δ nDCG@8</th><th>Precision@8</th><th>Faithfulness</th><th>Retrieval cost / question</th></tr></thead>
<tbody>{d_rows}</tbody></table>
<p class="note">Checks: a shuffled control (each question judged on another question's documents) scores 0.0%; the baseline judged
twice differs by 1.4 points; five stored benchmark runs of the baseline score 61.7 ± 3.4%. On two fresh query sets the winner
gained +7.1 and +12.1 points. The single-judge faithfulness values are not comparable with section 1's panel values.</p>
</body></html>"""

    md = ["# Search methods: benchmark results and cost", "", "## 1. Search methods on the repeated benchmark", "",
          "| Search method | Runs | Same category | Exact | Consistent | Mean \\|z\\| | Satisfactory | Faithfulness | Aligned | Strict coverage | nDCG@8 | Retrieval $/q | Total $/q | $/run | Time |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    md += [
        f"| {r['name']} | {r['runs']} | {r['mc_same']} | {r['mc_exact']} | {r['fc']} | {r['zlog']} | {r['zlog_sat']} | {r['faith']} | {r['aligned']} | {pct(r['coverage'])} | {r['ndcg_s']} | {money(r['retrieval'])} | {money(r['per_question'])} | ${r['run_cost']:.2f} | {r['time']} |"
        for r in bench
    ]
    md += ["", "## 2. Earlier optimizations (50 questions, 2026-09-21)", "",
           "| Method | Relevant docs | Docs with true value | Answer close | Answer in category | Retrieval $/q | Total $/q | Time |", "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    md += [
        f"| {n} | {rel}% | {truth}% | {close}% | {cat}% | {money(ret, 5)} | {money(tot, 5)} | {t} s |"
        for n, _, rel, truth, close, cat, ret, tot, t in STUDY
    ]
    md += ["", "## 3. Document-metric search on Europe PMC + LitSense (2026-10-16)", "",
           "| Configuration | Strict coverage | Δ strict (95% CI) | Category | nDCG@8 | Precision@8 | Faithfulness | Retrieval $/q |", "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for r in docs:
        d = r["vs"].get("strict")
        ds = (
            f"{100 * d['mean']:+.1f} ({100 * d['ci'][0]:+.1f} to {100 * d['ci'][1]:+.1f})"
            if d
            else ""
        )
        f = faith.get(r["name"])
        md.append(
            f"| {r['name']} | {pct(r['strict'])} | {ds} | {pct(r['category'])} | {r['ndcg']:.3f} | {pct(r['precision'])} | {pct(f['supported']) if f else '–'} | {money(r['retrieval'])} |"
        )
    return page, "\n".join(md) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    page, md = build()
    (OUT / "search_methods.html").write_text(page, encoding="utf-8")
    (OUT / "search_methods.md").write_text(md, encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={OUT / 'search_methods.pdf'}", (OUT / "search_methods.html").as_uri()],
        check=True, capture_output=True, timeout=120,
    )  # fmt: skip
    print(f"Wrote {OUT}/search_methods.html, .md and .pdf", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
