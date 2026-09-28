"""Build the benchmark results table (Markdown, HTML, JSON, and PDF) from the benchmark data.

Usage: python environment/results/scripts/make_retriever_comparison.py
       [RETRIEVAL_WS [SET_C_WS [OUT_DIR]]]
Reads the retriever comparison workspace (sets A and B under seven retrieval configurations;
default environment/results/retriever_comparison) and the set C workspace (answered from the case
information without retrieval; default environment/results/set_c). No API calls. Writes
retriever_comparison.md, .html, .json, and .pdf to OUT_DIR (default environment/results/); the
PDF is printed from the HTML by headless Google Chrome.

Each label's percentage is the share of all questions in its set whose voted label (the judge
panel's majority vote) it is; "no label" completes each metric to 100%. Cost and time cover every
environment component (Stages A-C, search, search model), not the judges, listed separately.
"""

from __future__ import annotations

import html
import json
import statistics
import subprocess
import sys
from pathlib import Path

from bench.config import BenchSettings
from bench.report import CONSISTENCY_LABELS, MASKED_LABELS, METRICS, Score, build_scores
from bench.run import CONFIGS
from bench.schemas import ConsistencyJudgment, Item, MaskedCorrectnessJudgment
from bench.workspace import Workspace, read_models

RESULTS = Path(__file__).resolve().parents[1]
ARGS = sys.argv[1:]
RETRIEVAL_WS = Workspace(Path(ARGS[0]) if len(ARGS) > 0 else RESULTS / "retriever_comparison")
SET_C_WS = Workspace(Path(ARGS[1]) if len(ARGS) > 1 else RESULTS / "set_c")
OUT = Path(ARGS[2]) if len(ARGS) > 2 else RESULTS
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# (configuration, row name, workspace)
ORDER = [
    ("current", "1. Current (Europe PMC + LitSense, without changes 1–4)", RETRIEVAL_WS),
    ("improved_1to4", "2. Current with changes 1–4", RETRIEVAL_WS),
    ("openrouter_exa_instant", "3. OpenRouter search: Exa instant, DeepSeek v4 Flash",
     RETRIEVAL_WS),
    ("openrouter_parallel_basic", "4. OpenRouter search: Parallel basic, DeepSeek v4 Flash",
     RETRIEVAL_WS),
    ("openrouter_perplexity", "5. OpenRouter search: Perplexity, DeepSeek v4 Flash",
     RETRIEVAL_WS),
    ("openrouter_google", "6. OpenRouter search: Google (native), Gemini 3.1 Flash Lite",
     RETRIEVAL_WS),
    ("openrouter_openai", "7. OpenRouter search: OpenAI (native), GPT-6-luna", RETRIEVAL_WS),
    ("case_information", "8. Case information only, no retrieval (DeepSeek v4 Flash 0731)",
     SET_C_WS),
]  # fmt: skip
METRIC_GROUPS = [
    ("Masked correctness (set A)", "mc", [*MASKED_LABELS, "no_label"]),
    ("Factual consistency (set B)", "fc", [*CONSISTENCY_LABELS, "no_label"]),
    ("Masked correctness (set C)", "mc_c", [*MASKED_LABELS, "no_label"]),
    ("Factual consistency (set C)", "fc_c", [*CONSISTENCY_LABELS, "no_label"]),
]
Row = dict[str, float | int | None]


def label_name(label: str) -> str:
    return "no label*" if label == "no_label" else label.replace("_", " ")


def summarise(scores: list[Score]) -> dict[str, Row]:
    """Per configuration: every label's share of its question set (None: set not run), the
    total cost, and the answer time."""
    rows: dict[str, Row] = {}
    for config, _, _ in ORDER:
        mine = [s for s in scores if s.config == config]
        if not mine:
            continue
        row: Row = {}
        for _, key, labels in METRIC_GROUPS:
            for label in labels:
                metric = f"{key}_{label}"
                qs = METRICS[metric][2]
                values = [METRICS[metric][1](s) for s in mine if s.question_set == qs]
                row[metric] = (
                    100 * sum(v for v in values if v is not None) / len(values) if values else None
                )
                row[f"n_{qs}"] = len(values)
        ran = [s for s in mine if s.ran]
        row["ran"] = len(ran)
        row["total_cost_usd"] = sum(s.total_cost for s in ran)
        row["retrieval_cost_usd"] = sum(s.retrieval_cost for s in ran)
        row["pipeline_cost_usd"] = sum(s.pipeline_cost for s in ran)
        row["mean_time_s"] = statistics.fmean(s.wall_time_s for s in ran)
        row["median_time_s"] = statistics.median(s.wall_time_s for s in ran)
        row["answered_from_literature"] = sum(s.path == "literature" for s in ran)
        row["answered_from_case"] = sum(s.path == "case_study" for s in ran)
        rows[config] = row
    return rows


def judge_costs(panel: list[str]) -> dict[str, dict[str, float]]:
    """Judging cost per workspace and judge model."""
    costs: dict[str, dict[str, float]] = {}
    for ws in (RETRIEVAL_WS, SET_C_WS):
        by_model: dict[str, float] = {}
        for path, cls in ((ws.masked_correctness, MaskedCorrectnessJudgment),
                          (ws.consistency, ConsistencyJudgment)):  # fmt: skip
            for judged in read_models(path, cls):
                if judged.judge_model in panel:
                    by_model[judged.judge_model] = by_model.get(judged.judge_model, 0.0) + sum(
                        c.cost_usd or 0.0 for c in judged.llm_calls
                    )
        costs[ws.root.name] = by_model
    return costs


def _pct(value: float | int | None) -> str:
    return "–" if value is None else f"{value:.1f}%"


def markdown(rows: dict[str, Row]) -> str:
    groups = [(title, [f"{key}_{label}" for label in labels], labels)
              for title, key, labels in METRIC_GROUPS]  # fmt: skip
    first = ["Metric →"]  # Markdown cannot merge cells: each metric heads its first label
    for title, cols, _ in groups:
        first += [title] + [""] * (len(cols) - 1)
    first += ["Environment cost and time", ""]
    second = ["Environment configuration ↓ / label →"]
    second += [label_name(label) for _, _, labels in groups for label in labels]
    second += ["Total cost (USD)", "Average answer time (s)"]
    lines = ["| " + " | ".join(first) + " |", "|" + "---|" * len(first),
             "| " + " | ".join(second) + " |"]  # fmt: skip
    for config, name, _ in ORDER:
        if config not in rows:
            continue
        r = rows[config]
        cells = [name] + [_pct(r[m]) for _, cols, _ in groups for m in cols]
        cells += [f"${r['total_cost_usd']:.3f}", f"{r['mean_time_s']:.1f}"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def html_page(rows: dict[str, Row], counts: dict[str, int], notes: list[str]) -> str:
    head1 = ['<th rowspan="2" class="cfg">Environment configuration</th>']
    head2 = []
    for title, _key, labels in METRIC_GROUPS:
        head1.append(f'<th colspan="{len(labels)}" class="group">{html.escape(title)}</th>')
        head2 += [f"<th>{html.escape(label_name(label))}</th>" for label in labels]
    head1.append('<th colspan="2" class="group">Environment cost and time</th>')
    head2 += ["<th>Total cost (USD)</th>", "<th>Average answer time (s)</th>"]
    # Highlight the best retrieval configuration(s) in the exact and consistent columns.
    best = {
        m: max(v for r in rows.values() if isinstance(v := r[m], float | int))
        for m in ("mc_exact", "fc_consistent")
        if any(r[m] is not None for r in rows.values())
    }
    body = []
    for config, name, _ in ORDER:
        if config not in rows:
            continue
        r = rows[config]
        cells = [f'<td class="cfg">{html.escape(name)}</td>']
        for _, key, labels in METRIC_GROUPS:
            for label in labels:
                metric = f"{key}_{label}"
                value = r[metric]
                cls = "nolabel" if label == "no_label" else ""
                if value is None:
                    cls = "na"
                elif metric in best and value == best[metric] and value > 0:
                    cls = "top"
                if label == labels[0]:
                    cls += " first"
                cells.append(f'<td class="{cls.strip()}">{_pct(value)}</td>')
        cells.append(f'<td class="first">${float(r["total_cost_usd"] or 0):.3f}</td>')
        cells.append(f"<td>{float(r['mean_time_s'] or 0):.1f}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    note_items = "".join(f"<li>{html.escape(n)}</li>" for n in notes)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Environment benchmark</title>
<style>
  @page {{ size: A3 landscape; margin: 12mm; }}
  body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1b1b1b;
         font-size: 12.5px; }}
  h1 {{ font-size: 21px; margin: 0 0 4px; }}
  p.sub {{ margin: 0 0 12px; color: #555; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #cfcfcf; padding: 5px 5px; text-align: center; }}
  thead tr:first-child th {{ background: #e9eef6; font-size: 13px; }}
  thead tr:nth-child(2) th {{ background: #f4f6fa; font-weight: 600; }}
  th.group, td.first {{ border-left: 2px solid #8a94a6; }}
  td.cfg, th.cfg {{ text-align: left; }}
  td.cfg {{ font-weight: 600; min-width: 230px; }}
  td.nolabel {{ color: #777; }}
  td.na {{ color: #b3b3b3; }}
  td.top {{ font-weight: 700; background: #eaf6ec; }}
  tbody tr:nth-child(even) td {{ background-color: #fafafa; }}
  tbody tr:nth-child(even) td.top {{ background: #eaf6ec; }}
  tbody tr:last-child td {{ border-top: 2px solid #8a94a6; }}
  ul {{ margin: 12px 0 0; padding-left: 16px; color: #333; }}
  li {{ margin: 3px 0; }}
</style></head><body>
<h1>Environment benchmark: masked correctness and factual consistency</h1>
<p class="sub">Percent of all questions in each set (set A: {counts["A"]}, set B: {counts["B"]},
set C: {counts["C"]}) by the judge panel's voted label; each metric's labels sum to 100%.
"–": the configuration did not answer that set.</p>
<table><thead><tr>{"".join(head1)}</tr><tr>{"".join(head2)}</tr></thead>
<tbody>{"".join(body)}</tbody></table>
<ul>{note_items}</ul>
</body></html>
"""


def main() -> None:
    panel = BenchSettings().judge_models
    items = {ws.root.name: read_models(ws.items, Item) for ws in (RETRIEVAL_WS, SET_C_WS)}
    scores: list[Score] = []
    for ws in (RETRIEVAL_WS, SET_C_WS):
        configs = [c for c, _, w in ORDER if w == ws]
        scores += build_scores(ws, items[ws.root.name], configs, panel)
    assert all(c in CONFIGS for c, _, _ in ORDER)
    rows = summarise(scores)
    costs = judge_costs(panel)
    all_items = [i for group in items.values() for i in group]
    counts = {qs: sum(i.question_set == qs for i in all_items) for qs in "ABC"}
    judged = sum(sum(by.values()) for by in costs.values())
    notes = [
        f"Questions from the {len({i.case_id for i in all_items})} cases in "
        f"cases/combined_272_whole_chunking.json: set A ({counts['A']}), a value hidden from "
        f"the case; set B ({counts['B']}), a value the case never states; set C "
        f"({counts['C']}), information the case states, written by an LLM "
        f"({BenchSettings().question_writer()}). Configurations 1-7 answered the same sets A "
        f"and B; configuration 8 answered set C.",
        f"Judge panel: {', '.join(panel)}. Each answer's label is the majority vote; with no "
        f"majority, the first (main) judge decides. Set C answers are graded by both metrics. "
        f"Judging cost ${judged:.2f} in total, not included in the costs above.",
        "* No label: medsim gave no answer (it found no usable literature, or for set C the "
        "case did not answer the question), the run failed, or there was no judge verdict; it "
        "is not a judge label.",
        "Total cost: every environment component for all questions of the configuration (medsim "
        "Stages A–C, search fees, and the search model's tokens), from OpenRouter's usage.cost. "
        "Average answer time: mean wall time per question, all components included.",
        "Configurations 6 and 7 use the model provider's own (native) search. Their documents "
        "are the search model's quotations or summaries of each cited source, not page "
        "excerpts as returned by Exa, Parallel, and Perplexity.",
        "Configuration 8 has retrieval switched off: medsim answers from the case information, "
        "or not at all, with deepseek/deepseek-v4-flash-0731 for every stage.",
        "Masked correctness labels: exact (the answer matches the true value), same category "
        "(same low/normal/high category, or the same finding with a minor detail wrong), "
        "different category, not comparable.",
    ]
    md = markdown(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "retriever_comparison.md").write_text(
        "# Environment benchmark\n\n" + md + "\n\n" + "\n".join(f"- {n}" for n in notes) + "\n",
        encoding="utf-8",
    )
    page = OUT / "retriever_comparison.html"
    page.write_text(html_page(rows, counts, notes), encoding="utf-8")
    (OUT / "retriever_comparison.json").write_text(
        json.dumps(
            {"panel": panel, "question_counts": counts, "judge_cost_usd": costs, "configs": rows},
            indent=2,
        ),
        encoding="utf-8",
    )
    pdf = OUT / "retriever_comparison.pdf"
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", page.as_uri()],
        check=True, capture_output=True,
    )  # fmt: skip
    print(md)
    print(f"\nWrote {pdf}", file=sys.stderr)


if __name__ == "__main__":
    main()
