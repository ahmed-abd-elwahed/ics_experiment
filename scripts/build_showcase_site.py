"""Build the showcase site: a landing page with two walkthroughs, one per experiment.

- DDx experiment: one case run of the differential diagnosis framework, stepped through its loop
  (calculate disease probabilities, check differentiation, retrieve new information, update the
  case representation). Taken from a DDx-Experiment run record.
- ICS experiment: the Clinician's View of the same case, for the four information collection
  strategies, from an ICS experiment record.

The page is one self-contained HTML file (site/index.html), so it can be published as is. The
extracted case data is also kept in site/data/ so the page can be rebuilt without the records.

    python scripts/build_showcase_site.py                 # extract from the records, then build
    python scripts/build_showcase_site.py --from-saved    # build from site/data/ only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = SITE / "data"

CASE_ID = "PMC7520668_01"

DDX_REPO = Path.home() / "DDx-Experiment"
DDX_RECORD = DDX_REPO / "data/runs/final/table/gpt_5.4_mini/framework/runs_record_0.json"
DDX_RUN_INDEX = 130  # the file holds two runs of this case; this is the first
DDX_CASES = DDX_REPO / "data/combined_272_whole_chunking.json"
# The framework's default stopping threshold (framework.py). The experiment itself turned it off
# and always ran 8 rounds; the walkthrough replays the run as if the default were on.
DDX_THRESHOLD = 0.5
# Where each answer comes from in the case text, for highlighting (checked against the text below).
DDX_SPANS = [
    [
        "Glomerular filtration rate declined by >5 ml/min/1.73 m2 per year",
        "creatinine 4.3 mg/dL",
        "urine protein/creatinine ratio 2.2",
        "subnephrotic-range proteinuria",
    ],
    ["SPEP, UPEP, and serum free light chains without abnormalities"],
    [
        "Kidney biopsy: light microscopy with normocellular glomeruli, uniform capillary walls, prominent "
        "podocytes with foamy cytoplasm; ultrastructural exam with osmophilic lamellated inclusions in "
        "podocytes with concentric/striped appearance (myelin-like lamellated inclusions)"
    ],
]

ICS_RECORD = ROOT / "records/strategies_272_8it.json"
ICS_STRATEGY_ORDER = ["hypothesis", "knowledge", "channel", "sequence"]


def extract_ddx() -> dict:
    record = json.loads(DDX_RECORD.read_text())
    run = record["runs"][DDX_RUN_INDEX]
    assert run["case_id"] == CASE_ID, run["case_id"]
    case = next(c for c in json.loads(DDX_CASES.read_text()) if c["case_id"] == CASE_ID)
    case_text = case["chunked_case_info"][0]

    history = run["ddx_history"]
    questions = run["retrieved_case_information_history"]
    stop = next(i for i, ddx in enumerate(history) if max(p for _, p in ddx) >= DDX_THRESHOLD)
    rounds = []
    for i in range(stop + 1):
        entry = {"ddx": [[name, p] for name, p in history[i]]}
        if i < stop:
            entry["question"] = questions[i]["case_info_query"]
            entry["answer"] = questions[i]["retrieved_case_info"]
            entry["spans"] = DDX_SPANS[i]
            for span in entry["spans"]:
                assert span.lower() in case_text.lower(), span
        rounds.append(entry)
    return {
        "case_id": CASE_ID,
        "diagnosis": case["diagnosis"],
        "background": case["background_and_presentation"],
        "case_text": case_text,
        "model": run["llm_model_name"],
        "environment_model": "google/gemini-3-flash-preview",
        "threshold": DDX_THRESHOLD,
        "rounds_in_experiment": run["number_of_iterations"],
        "final_in_experiment": history[-1][0],
        "source": f"{DDX_RECORD.relative_to(DDX_REPO)} · run {DDX_RUN_INDEX}",
        "rounds": rounds,
    }


def trim_response(response: dict | None) -> dict | None:
    if not response:
        return None
    params = response.get("retriever_parameters") or {}
    result = response.get("literature_search_result") or None
    return {
        "answer_source": response.get("answer_source"),
        "evidence": response.get("evidence") or [],
        "confidence": response.get("confidence"),
        "literature_search": bool(response.get("literature_search")),
        "retriever_parameters": {
            "path": params.get("path"),
            "multi_part": params.get("multi_part"),
            "sub_queries": [{"path": s.get("path")} for s in params.get("sub_queries") or []],
            "literature_query": params.get("literature_query"),
            "excluded_source_docs": params.get("excluded_source_docs") or [],
        },
        "literature_search_result": result
        and {
            "query": result.get("query"),
            "documents": [
                {k: d.get(k) for k in ("doc_id", "title", "url", "source", "journal", "pub_year")}
                for d in result.get("documents") or []
            ],
        },
    }


def extract_ics() -> dict:
    record = json.loads(ICS_RECORD.read_text())
    runs = [r for r in record["case_runs"] if r["case_id"] == CASE_ID]
    runs.sort(key=lambda r: ICS_STRATEGY_ORDER.index(r["strategy_name"]) if r["strategy_name"] in ICS_STRATEGY_ORDER else 99)
    case_runs = []
    for r in runs:
        case_runs.append(
            {
                "case_id": r["case_id"],
                "strategy": r["strategy"],
                "strategy_name": r["strategy_name"],
                "status": r["status"],
                "stop_reason": r["stop_reason"],
                "case": {k: r["case"][k] for k in ("case_id", "diagnosis", "narrative")},
                "diagnosis": r["diagnosis"]
                and {"differential": r["diagnosis"].get("differential") or [], "error": r["diagnosis"].get("error")},
                "iterations": [
                    {
                        "question": it["question"],
                        "answer": it["answer"],
                        "answer_source": it["answer_source"],
                        "error": it.get("error"),
                        "strategy_trace": it.get("strategy_trace"),
                        "environment_response": trim_response(it.get("environment_response")),
                    }
                    for it in r["iterations"]
                ],
            }
        )
    settings = record.get("environment_settings") or {}
    return {
        "source": f"{ICS_RECORD.relative_to(ROOT)}",
        "environment_settings": {k: settings.get(k) for k in ("default_model", "enabled_sources")},
        "strategies": {name: {"description": s.get("description")} for name, s in (record.get("strategies") or {}).items()},
        "case_runs": case_runs,
    }


def build(ddx: dict, ics: dict) -> None:
    template = (SITE / "template.html").read_text()
    data = json.dumps({"ddx": ddx, "ics": ics}, ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")  # never close the script tag early
    marker = "/*__DATA__*/null"
    assert template.count(marker) == 1
    (SITE / "index.html").write_text(template.replace(marker, data))
    print(f"Wrote {SITE / 'index.html'} ({(SITE / 'index.html').stat().st_size / 1024:.0f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-saved", action="store_true", help="build from site/data/ without reading the records")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    if args.from_saved:
        ddx = json.loads((DATA / "ddx_case.json").read_text())
        ics = json.loads((DATA / "ics_case.json").read_text())
    else:
        ddx, ics = extract_ddx(), extract_ics()
        (DATA / "ddx_case.json").write_text(json.dumps(ddx, ensure_ascii=False, indent=1))
        (DATA / "ics_case.json").write_text(json.dumps(ics, ensure_ascii=False, indent=1))
    build(ddx, ics)


if __name__ == "__main__":
    main()
