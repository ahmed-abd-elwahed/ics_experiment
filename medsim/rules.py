"""Rule-based query handling: normalization, variable/timepoint keys, multi-part splitting.

Deliberately simple and deterministic. Paraphrases that use no known keyword are not
detected as repeats here; the orchestrator also checks the ledger after Stage B.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

_STOPWORDS = frozenset(
    {
        "what", "whats", "is", "was", "are", "were", "the", "a", "an", "patient", "patients",
        "his", "her", "their", "of", "please", "tell", "me", "can", "you", "could", "current",
        "currently", "s", "do", "does", "did", "how", "much", "many",
    }
)  # fmt: skip

VARIABLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "temperature": ("body temperature", "temperature", "temp"),
    "heart_rate": ("heart rate", "pulse rate", "pulse"),
    "respiratory_rate": ("respiratory rate", "respiration rate", "breathing rate"),
    "blood_pressure": ("blood pressure", "bp"),
    "oxygen_saturation": ("oxygen saturation", "spo2", "sao2", "o2 sat", "o2 saturation",
                          "pulse oximetry", "pulse ox"),
    "weight": ("body weight", "weight"),
    "height": ("height",),
    "bmi": ("body mass index", "bmi"),
    "glucose": ("blood glucose", "glucose", "blood sugar"),
    "hemoglobin": ("hemoglobin", "haemoglobin", "hgb"),
    "white_cell_count": ("white blood cell count", "white blood cells", "white cell count", "wbc",
                         "leukocyte count"),
    "platelet_count": ("platelet count", "platelets"),
    "creatinine": ("serum creatinine", "creatinine"),
    "sodium": ("serum sodium", "sodium"),
    "potassium": ("serum potassium", "potassium"),
    "c_reactive_protein": ("c-reactive protein", "c reactive protein", "crp"),
    "lactate": ("lactic acid", "lactate"),
    "procalcitonin": ("procalcitonin",),
}  # fmt: skip

_KEYWORD_PATTERNS: list[tuple[re.Pattern[str], str, int]] = sorted(
    (
        (re.compile(rf"(?<![\w-]){re.escape(kw)}(?![\w-])", re.I), var, len(kw))
        for var, kws in VARIABLE_KEYWORDS.items()
        for kw in kws
    ),
    key=lambda item: -item[2],
)

_TIMEPOINT_NUMBERED = re.compile(
    r"\b(?P<unit>hospital day|post-?operative day|post-?op day|pod|day|week|hour|month)\s*#?\s*"
    r"(?P<n>\d+)\b",
    re.I,
)
_TIMEPOINT_RELATIVE = re.compile(
    r"\b(?P<n>\d+)\s*(?P<unit>hours?|days?|weeks?|months?)\s+(?:after|post|into|later)\b", re.I
)
_TIMEPOINT_NAMED = re.compile(
    r"\b(admission|admitted|discharge|discharged|baseline|presentation)\b", re.I
)
_NAMED_CANON = {"admitted": "admission", "discharged": "discharge", "presentation": "admission"}

_SPLIT = re.compile(r"\s*(?:,|;|&|\band\b|\bas well as\b|\bplus\b)\s*", re.I)


def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace(chr(0x2019), "'")  # curly apostrophe


def normalize_query(query: str) -> str:
    text = _nfkc(query).lower()
    text = re.sub(r"'s\b", "", text)
    text = re.sub(r"[^\w\s/.%-]", " ", text)
    tokens = [t.strip(".") for t in text.split()]
    return " ".join(t for t in tokens if t and t not in _STOPWORDS)


def find_variables(text: str) -> list[tuple[int, int, str]]:
    """Return non-overlapping (start, end, variable) matches, longest keyword first."""
    taken: list[tuple[int, int, str]] = []
    for pattern, var, _ in _KEYWORD_PATTERNS:
        for m in pattern.finditer(text):
            if all(m.end() <= s or m.start() >= e for s, e, _ in taken):
                taken.append((m.start(), m.end(), var))
    return sorted(taken)


def canonical_variable(text: str) -> str | None:
    found = {var for _, _, var in find_variables(_nfkc(text))}
    return found.pop() if len(found) == 1 else None


def timepoint(text: str) -> str | None:
    text = _nfkc(text)
    if m := _TIMEPOINT_NUMBERED.search(text):
        unit = m.group("unit").lower().replace("-", "")
        unit = {"postoperative day": "pod", "postop day": "pod", "hospital day": "day"}.get(
            unit, unit
        )
        return f"{unit}{int(m.group('n'))}"
    if m := _TIMEPOINT_RELATIVE.search(text):
        unit = m.group("unit").lower().rstrip("s")
        return f"{unit}{int(m.group('n'))}"
    if m := _TIMEPOINT_NAMED.search(text):
        word = m.group(1).lower()
        return _NAMED_CANON.get(word, word)
    return None


_AGE_PATTERNS: list[tuple[re.Pattern[str], str | None]] = [
    (re.compile(r"\b(?:newborns?|neonates?|neonatal|preterm|premature (?:infant|baby|neonate))\b"
                r"|\b\d{1,2}[- ](?:day|week)s?[- ]old\b", re.I), "neonate"),
    (re.compile(r"\b\d{1,2}[- ]months?[- ]old\b", re.I), "child"),
    (re.compile(r"\b(\d{1,3})[- ](?:year|yr)s?[- ]old\b|\baged (\d{1,3})\b"
                r"|\b(\d{1,3}) ?(?:y/o|yo)\b", re.I), None),
]  # fmt: skip


def age_group(text: str) -> Literal["neonate", "child", "adult"] | None:
    """The patient's age group from the first age statement in the case text."""
    text = _nfkc(text)
    first: tuple[int, str] | None = None
    for pattern, group in _AGE_PATTERNS:
        match = pattern.search(text)
        if match is None or (first is not None and match.start() >= first[0]):
            continue
        if group is None:
            years = int(next(g for g in match.groups() if g))
            group = "adult" if years >= 18 else "child"
        first = (match.start(), group)
    return first[1] if first else None  # type: ignore[return-value]


def ledger_key(variable: str, point: str | None) -> str:
    return f"{variable}@{point or 'unspecified'}"


def split_multipart(query: str) -> list[str]:
    """Split "temperature and heart rate" style questions into one sub-query per variable.

    Only splits when every conjunction-separated segment names exactly one known variable
    and at least two distinct variables are present; otherwise returns ``[query]``.
    """
    text = _nfkc(query).strip()
    segments = [s for s in _SPLIT.split(text) if s.strip()]
    if len(segments) < 2:
        return [query]
    per_segment = [find_variables(s) for s in segments]
    if any(len({v for _, _, v in found}) != 1 for found in per_segment):
        return [query]
    if len({found[0][2] for found in per_segment}) < 2:
        return [query]

    first_start = per_segment[0][0][0]
    last_end = per_segment[-1][-1][1]
    prefix = segments[0][:first_start]
    trailing = segments[-1][last_end:]
    if text.endswith("?") and not trailing.endswith("?"):
        trailing = trailing + "?"

    sub_queries: list[str] = []
    last = len(segments) - 1
    for i, (segment, found) in enumerate(zip(segments, per_segment, strict=True)):
        start = found[0][0] if i == 0 else 0
        end = found[-1][1] if i == last else len(segment.rstrip("?"))
        core = segment[start:end].strip()
        sub_queries.append(f"{prefix}{core}{trailing}".strip())
    return sub_queries
