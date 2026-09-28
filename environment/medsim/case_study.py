"""Case-study loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from medsim.errors import ConfigError
from medsim.models import CaseStudy


def case_from_record(record: dict[str, Any]) -> CaseStudy:
    """Accept both the case dataset format and ``CaseStudy``-shaped records.

    Dataset format: ``{"case_id", "case_information", "diagnosis"}``; ``case_information``
    becomes the narrative.
    """
    if "case_information" in record:
        return CaseStudy(
            case_id=str(record["case_id"]),
            diagnosis=str(record["diagnosis"]),
            narrative=str(record["case_information"]),
        )
    return CaseStudy.model_validate(record)


def load_cases(path: Path) -> dict[str, CaseStudy]:
    """Every case in a dataset file (a JSON list, or a single case), keyed by case id in order."""
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else [data]
    cases: dict[str, CaseStudy] = {}
    for case in (case_from_record(r) for r in records):
        if case.case_id in cases:
            raise ValueError(f"Duplicate case id {case.case_id!r} in {path}.")
        cases[case.case_id] = case
    return cases


def load_case_study(path: str | Path) -> CaseStudy:
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read case study {path}: {exc}") from exc
    try:
        case = case_from_record(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Case study {path} is not valid JSON: {exc}") from exc
    except (ValidationError, KeyError, TypeError, AttributeError) as exc:
        raise ConfigError(
            f"Case study {path} is neither a dataset record nor a CaseStudy: {exc}"
        ) from exc
    if not case.diagnosis.strip():
        raise ConfigError(f"Case study {path} has an empty 'diagnosis'.")
    if not case.narrative.strip():
        raise ConfigError(f"Case study {path} has an empty 'narrative'.")
    return case


def case_study_prompt_block(case: CaseStudy) -> str:
    """Render the case study for inclusion in prompts."""
    return json.dumps(case.model_dump(mode="json"), indent=2, ensure_ascii=False)
