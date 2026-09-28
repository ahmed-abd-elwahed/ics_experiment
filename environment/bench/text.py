"""Case loading and the deterministic text checks the benchmark relies on."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

# The dataset format belongs to the environment; re-exported for bench modules.
from medsim.case_study import case_from_record as case_from_record
from medsim.case_study import load_cases as load_cases
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


def case_text(case: CaseStudy) -> str:
    """Everything a question could be answered from: the case information."""
    return case.narrative.strip()


def patient_summary(case: CaseStudy) -> str:
    """Short patient description for the judge (age, sex, setting)."""
    text = case_text(case)
    return text if len(text) <= 600 else text[:600].rsplit(" ", 1)[0] + " …"


def source_pmcid(case_id: str) -> str | None:
    match = _PMC_CASE.match(case_id)
    return match.group(1).upper() if match else None


def with_redacted_text(case: CaseStudy, narrative: str) -> CaseStudy:
    return case.model_copy(update={"narrative": narrative})


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
