"""Case-study loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from medsim.errors import ConfigError
from medsim.models import CaseStudy


def case_from_record(record: dict[str, Any]) -> CaseStudy:
    """Accept both the combined case file format and ``CaseStudy``-shaped records.

    Combined format: ``chunked_case_info`` joined with blank lines becomes the narrative, and
    ``background_and_presentation`` goes into metadata (the mapping used for earlier live runs).
    """
    if "chunked_case_info" in record:
        chunks = record["chunked_case_info"]
        narrative = "\n\n".join(chunks) if isinstance(chunks, list) else str(chunks)
        background = str(record.get("background_and_presentation") or "")
        return CaseStudy(
            case_id=str(record["case_id"]),
            diagnosis=str(record["diagnosis"]),
            narrative=narrative,
            metadata={"background_and_presentation": background} if background else {},
        )
    return CaseStudy.model_validate(record)


def load_cases(path: Path) -> dict[str, CaseStudy]:
    """Every case in a dataset file (a JSON list, or a single case), keyed by case id in order."""
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else [data]
    cases = [case_from_record(r) for r in records]
    return {c.case_id: c for c in cases}


def load_case_study(path: str | Path) -> CaseStudy:
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read case study {path}: {exc}") from exc
    try:
        case = CaseStudy.model_validate(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Case study {path} is not valid JSON: {exc}") from exc
    except ValidationError as exc:
        raise ConfigError(f"Case study {path} does not match the CaseStudy schema: {exc}") from exc
    if not case.diagnosis.strip():
        raise ConfigError(f"Case study {path} has an empty 'diagnosis'.")
    if not case.narrative.strip():
        raise ConfigError(f"Case study {path} has an empty 'narrative'.")
    return case


def case_study_prompt_block(case: CaseStudy) -> str:
    """Render the case study for inclusion in prompts."""
    return json.dumps(case.model_dump(mode="json"), indent=2, ensure_ascii=False)
