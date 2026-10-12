"""Evaluate an experiment record: code every diagnosis, rank, and average per strategy.

    .venv/bin/python -m evaluation records/<record>.json

Writes ``<record>.eval.json`` next to the record: the metrics per strategy, and for every case
run the true diagnosis and each predicted diagnosis with the ICD-11 code it was given.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from evaluation.icd import SEARCH_URL, ICDCoder, credentials
from evaluation.metrics import METRICS, case_scores, mean_scores, rank_of, ranked_codes
from experiment.record import CaseRun, ExperimentRecord, load_record
from medsim.errors import MedSimError

Coder = Callable[[Sequence[str]], list[str]]


def evaluate_case_run(run: CaseRun, code: dict[str, str]) -> dict[str, Any]:
    truth = code[run.case.diagnosis]
    differential = run.diagnosis.differential if run.diagnosis else []
    predictions = [
        {"name": d.name, "probability": d.probability, "icd_code": code[d.name]}
        for d in differential
    ]
    codes = ranked_codes([(code[d.name], d.probability) for d in differential])
    rank = rank_of(truth, codes)
    return {
        "index": run.index,
        "case_id": run.case_id,
        "strategy": run.strategy,
        "status": run.status,
        "stop_reason": run.stop_reason,
        "questions": len(run.iterations),
        "true_diagnosis": run.case.diagnosis,
        "true_icd_code": truth,
        "predictions": predictions,
        "ranked_codes": codes,
        "rank": rank,
        "scores": case_scores(rank),
    }


def strategy_summary(rows: list[dict[str, Any]], runs: list[CaseRun]) -> dict[str, Any]:
    """Every case run counts: one without a differential, without a coded prediction, or whose
    true diagnosis has no ICD code scores zero."""
    n = len(rows)
    return {
        "case_runs": n,
        "metrics": mean_scores([row["rank"] for row in rows]),
        "without_differential": sum(not row["predictions"] for row in rows),
        "without_coded_prediction": sum(not row["ranked_codes"] for row in rows),
        "true_diagnosis_uncoded": sum(not row["true_icd_code"] for row in rows),
        "predictions_uncoded": sum(not p["icd_code"] for row in rows for p in row["predictions"]),
        "predictions": sum(len(row["predictions"]) for row in rows),
        "mean_questions": round(sum(row["questions"] for row in rows) / n, 2) if n else 0.0,
        "stop_reasons": {
            reason: sum(row["stop_reason"] == reason for row in rows)
            for reason in sorted({row["stop_reason"] for row in rows})
        },
        "cost_usd": round(sum(run.cost_usd for run in runs), 6),
        "mean_case_run_seconds": round(sum(r.elapsed_s for r in runs) / n, 2) if n else 0.0,
    }


def evaluate_record(record: ExperimentRecord, coder: Coder) -> dict[str, Any]:
    names = list(
        dict.fromkeys(
            name
            for run in record.case_runs
            for name in (
                run.case.diagnosis,
                *(d.name for d in (run.diagnosis.differential if run.diagnosis else [])),
            )
        )
    )
    code = dict(zip(names, coder(names), strict=True))
    rows = [evaluate_case_run(run, code) for run in record.case_runs]
    strategies = list(dict.fromkeys(run.strategy for run in record.case_runs))
    return {
        "format": "ics-experiment-evaluation",
        "record": record.output,
        "record_status": record.status,
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "coding": {
            "system": "ICD-11 MMS 2024-01",
            "endpoint": SEARCH_URL,
            "method": "first result of the flexible search for the diagnosis name",
            "names": len(names),
            "names_uncoded": sum(not c for c in code.values()),
        },
        "metrics": list(METRICS),
        "by_strategy": {
            key: strategy_summary(
                [row for row in rows if row["strategy"] == key],
                [run for run in record.case_runs if run.strategy == key],
            )
            for key in strategies
        },
        "case_runs": rows,
    }


def table(evaluation: dict[str, Any]) -> str:
    shown = ("hit_rate@1", "hit_rate@3", "hit_rate@5", "hit_rate@10", "ndcg@10", "mrr")
    width = max([len("strategy"), *(len(key) for key in evaluation["by_strategy"])])
    lines = ["  ".join(["strategy".ljust(width), *(m.rjust(11) for m in shown), "  runs"])]
    for key, summary in evaluation["by_strategy"].items():
        cells = [f"{summary['metrics'][m]:.3f}".rjust(11) for m in shown]
        lines.append("  ".join([key.ljust(width), *cells, str(summary["case_runs"]).rjust(6)]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evaluation", description=__doc__.splitlines()[0])
    parser.add_argument("record", type=Path, help="an experiment record (.json or .partial.jsonl)")
    parser.add_argument("--output", type=Path, help="default: <record>.eval.json")
    parser.add_argument("--workers", type=int, default=10, help="parallel ICD lookups")
    args = parser.parse_args(argv)
    load_dotenv(".env")  # the project root, where this is run from
    try:
        record = load_record(args.record)
        coder = ICDCoder(*credentials(), workers=args.workers)
        try:
            evaluation = evaluate_record(record, coder.codes)
        finally:
            coder.close()
    except (MedSimError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    name = args.record.name.removesuffix(".partial.jsonl").removesuffix(".json")
    output = args.output or args.record.with_name(f"{name}.eval.json")
    output.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8")
    print(table(evaluation))
    print(f"\nSaved {output}")
    return 0
