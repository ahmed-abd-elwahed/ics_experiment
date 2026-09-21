"""Case-study loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from medsim.errors import ConfigError
from medsim.models import CaseStudy


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
