"""Case loading and the deterministic text checks the benchmark relies on."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from medsim.models import CaseStudy

_WS = re.compile(r"\s+")
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…|\[…\]|\[\.\.\.\])\s*")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_PMC_CASE = re.compile(r"^(PMC\d+)", re.I)
_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "−": "-"})

# A number followed by a clinical unit: the cheap prefilter for cases worth extracting.
HAS_MEASUREMENT = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mg/dl|mg/l|g/dl|g/l|mmol/l|[µμu]mol/l|meq/l|u/l|iu/l|ng/ml|pg/ml|mmhg|"
    r"°\s*[cf]|bpm|beats|/min|breaths|%|[x×]\s*10|/mm3|/[µμu]l|kg\b)",
    re.I,
)


# --- cases --------------------------------------------------------------------------------------


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
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else [data]
    cases = [case_from_record(r) for r in records]
    return {c.case_id: c for c in cases}


def background(case: CaseStudy) -> str:
    return str(case.metadata.get("background_and_presentation") or "")


def case_text(case: CaseStudy) -> str:
    """Everything a question could be answered from: background plus narrative."""
    return f"{background(case)}\n\n{case.narrative}".strip()


def patient_summary(case: CaseStudy) -> str:
    """Short patient description for the judge (age, sex, setting)."""
    text = background(case) or case.narrative
    return text if len(text) <= 600 else text[:600].rsplit(" ", 1)[0] + " …"


def source_pmcid(case_id: str) -> str | None:
    match = _PMC_CASE.match(case_id)
    return match.group(1).upper() if match else None


def with_redacted_text(case: CaseStudy, narrative: str, background_text: str) -> CaseStudy:
    metadata = dict(case.metadata)
    if background_text or "background_and_presentation" in metadata:
        metadata["background_and_presentation"] = background_text
    return case.model_copy(update={"narrative": narrative, "metadata": metadata})


# --- normalisation and matching -----------------------------------------------------------------


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE).casefold()
    return _WS.sub(" ", text).strip()


def contains_verbatim(haystack: str, needle: str) -> bool:
    needle_n = normalize(needle).strip(" \"'")
    return bool(needle_n) and needle_n in normalize(haystack)


def quote_found(quote: str, text: str) -> bool:
    """True if every ellipsis-separated fragment of ``quote`` occurs in ``text``, in order."""
    fragments = [f.strip(" \"'") for f in _ELLIPSIS.split(normalize(quote))]
    fragments = [f for f in fragments if f]
    if not fragments:
        return False
    haystack = normalize(text)
    position = 0
    for fragment in fragments:
        index = haystack.find(fragment, position)
        if index < 0:
            return False
        position = index + len(fragment)
    return True


def value_pattern(value: str) -> re.Pattern[str]:
    core = value.strip().lstrip("<>≤≥~ ").strip()
    return re.compile(rf"(?<![\d.,]){re.escape(core)}(?![\d]|[.,]\d)")


def count_value(text: str, value: str) -> int:
    return len(value_pattern(value).findall(unicodedata.normalize("NFKC", text)))


def numbers(text: str) -> Counter[str]:
    return Counter(_NUMBER.findall(unicodedata.normalize("NFKC", text)))


def numeric_value(value: str) -> float | None:
    """A single number ("2.4", "15,200", "<0.5"); None for "100/60" or ranges."""
    core = value.strip().lstrip("<>≤≥~ ").replace(",", "")
    try:
        return float(core)
    except ValueError:
        return None


def check_redaction(original: str, redacted: str, span: str, value: str) -> str | None:
    """Why a redaction is unusable, or None if it passes the deterministic checks."""
    if contains_verbatim(redacted, span):
        return "span_still_present"
    removed_here = count_value(span, value)
    if count_value(redacted, value) > count_value(original, value) - max(removed_here, 1):
        return "value_still_present"
    if numbers(redacted) - numbers(original):
        return "numbers_added"
    removed = len(original) - len(redacted)
    if removed > max(3 * len(span), 200):
        return "too_much_removed"
    if removed < -20:
        return "text_added"
    return None


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize(text)).strip("_")[:40] or "x"
