"""Run a record's failed case runs again and save a merged record.

    .venv/bin/python -m experiment.rerun records/<record>.json

A case run failed if it ended in an error or its diagnosis could not be produced. Each strategy
with failures is run again on just those cases, with the record's own config, into
``<record>_rerun_<strategy>.json``. ``<record>_merged.json`` is the original record with the
failed case runs replaced by the new ones and listed under ``reruns``; the original record is
left as it was.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from experiment.record import CaseRun, load_record, summarize
from experiment.runner import ExperimentRunner
from medsim.errors import MedSimError


def failed(run: CaseRun) -> str | None:
    """Why the case run needs another attempt, or None if it is complete."""
    if run.status == "error":
        return run.error or "error"
    if run.diagnosis is not None and run.diagnosis.error:
        return run.diagnosis.error
    return None


def rerun(path: Path) -> Path | None:
    record = load_record(path)
    failures = {(r.case_id, r.strategy): failed(r) for r in record.case_runs if failed(r)}
    if not failures:
        return None
    replacements: dict[tuple[str, str], tuple[CaseRun, str]] = {}
    for spec in record.config.strategies:
        case_ids = [case_id for case_id, key in failures if key == spec.key]
        if not case_ids:
            continue
        output = path.with_name(f"{path.stem}_rerun_{spec.key}.json")
        config = record.config.model_copy(
            update={
                "name": f"{record.name}_rerun_{spec.key}",
                "case_ids": case_ids,
                "max_cases": None,
                "strategies": [spec],
                "output": str(output),
            }
        )
        print(f"{spec.key}: running {len(case_ids)} failed case runs again", file=sys.stderr)
        again = ExperimentRunner(config).run()
        for run in again.case_runs:
            replacements[(run.case_id, run.strategy)] = (run, again.output)
    case_runs, reruns = [], []
    for run in record.case_runs:
        new = replacements.get((run.case_id, run.strategy))
        if new is None or failed(new[0]):  # still failing: keep the first attempt
            case_runs.append(run)
            continue
        case_runs.append(new[0].model_copy(update={"index": run.index}))
        reruns.append(
            {
                "case_id": run.case_id,
                "strategy": run.strategy,
                "first_error": failures[(run.case_id, run.strategy)],
                "from_record": new[1],
            }
        )
    merged_path = path.with_name(f"{path.stem}_merged.json")
    merged = record.model_copy(
        update={
            "output": str(merged_path),
            "case_runs": case_runs,
            "summary": summarize(case_runs, record.config.strategy_keys),
            "reruns": reruns,
        }
    )
    merged_path.write_text(merged.model_dump_json(indent=2), encoding="utf-8")
    print(f"{len(reruns)} of {len(failures)} failed case runs replaced.", file=sys.stderr)
    return merged_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="experiment.rerun", description=__doc__.splitlines()[0])
    parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    try:
        merged = rerun(args.record)
    except (MedSimError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(merged if merged else "No failed case runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
