"""Deterministic clinical unit handling so repeated facts never disagree across units."""

from __future__ import annotations

import re
from collections.abc import Callable

_ALIASES: dict[str, str] = {
    "°c": "°C", "ºc": "°C", "c": "°C", "degc": "°C", "deg c": "°C", "celsius": "°C",
    "degrees celsius": "°C", "°f": "°F", "ºf": "°F", "f": "°F", "degf": "°F", "deg f": "°F",
    "fahrenheit": "°F", "degrees fahrenheit": "°F",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm", "centimetre": "cm", "centimetres": "cm",
    "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "in": "in", "inch": "in", "inches": "in",
    "g/dl": "g/dL", "g/l": "g/L", "mg/dl": "mg/dL", "mmol/l": "mmol/L",
    "µmol/l": "µmol/L", "umol/l": "µmol/L", "μmol/l": "µmol/L",
}  # fmt: skip

_Conv = Callable[[float], float]

_GENERIC: dict[tuple[str, str], _Conv] = {
    ("°C", "°F"): lambda v: v * 9 / 5 + 32,
    ("°F", "°C"): lambda v: (v - 32) * 5 / 9,
    ("kg", "lb"): lambda v: v / 0.45359237,
    ("lb", "kg"): lambda v: v * 0.45359237,
    ("cm", "in"): lambda v: v / 2.54,
    ("in", "cm"): lambda v: v * 2.54,
    ("m", "cm"): lambda v: v * 100,
    ("cm", "m"): lambda v: v / 100,
    ("m", "in"): lambda v: v * 100 / 2.54,
    ("in", "m"): lambda v: v * 2.54 / 100,
    ("g/dL", "g/L"): lambda v: v * 10,
    ("g/L", "g/dL"): lambda v: v / 10,
}

# Analyte-specific molar conversions.
_ANALYTE: dict[str, dict[tuple[str, str], _Conv]] = {
    "glucose": {
        ("mg/dL", "mmol/L"): lambda v: v / 18.016,
        ("mmol/L", "mg/dL"): lambda v: v * 18.016,
    },
    "creatinine": {
        ("mg/dL", "µmol/L"): lambda v: v * 88.42,
        ("µmol/L", "mg/dL"): lambda v: v / 88.42,
    },
}

_DECIMALS: dict[str, int] = {
    "°C": 1, "°F": 1, "kg": 1, "lb": 0, "cm": 0, "m": 2, "in": 1,
    "g/dL": 1, "g/L": 0, "mg/dL": 1, "mmol/L": 1, "µmol/L": 0,
}  # fmt: skip

# Explicit unit requests in a question ("in Fahrenheit", "°F", "mmol/L").
_REQUEST_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"fahrenheit|[°º]\s*f\b|\bdeg(?:rees)?\s*f\b", re.I), "°F"),
    (re.compile(r"celsius|centigrade|[°º]\s*c\b|\bdeg(?:rees)?\s*c\b", re.I), "°C"),
    (re.compile(r"\b(?:lbs?|pounds?)\b", re.I), "lb"),
    (re.compile(r"\b(?:kg|kilograms?)\b", re.I), "kg"),
    (re.compile(r"\b(?:inches|inch)\b", re.I), "in"),
    (re.compile(r"\b(?:cm|centimet(?:er|re)s?)\b", re.I), "cm"),
    (re.compile(r"mmol\s*/\s*l\b", re.I), "mmol/L"),
    (re.compile(r"[µμu]mol\s*/\s*l\b", re.I), "µmol/L"),
    (re.compile(r"mg\s*/\s*dl\b", re.I), "mg/dL"),
    (re.compile(r"\bg\s*/\s*dl\b", re.I), "g/dL"),
    (re.compile(r"\bg\s*/\s*l\b", re.I), "g/L"),
]

_VALUE_UNIT = re.compile(
    r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[°º]\s*[CF]\b|deg(?:rees)?\s*[CF]\b|celsius|fahrenheit"
    r"|kg\b|lbs?\b|cm\b|mmol/L|[µμu]mol/L|mg/dL|g/dL|g/L)",
    re.I,
)


def normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    key = re.sub(r"\s+", " ", unit.strip().lower()).replace("degrees ", "deg ")
    key = key.replace("° ", "°").replace("º ", "º")
    if key in _ALIASES:
        return _ALIASES[key]
    compact = key.replace(" ", "")
    return _ALIASES.get(compact, unit.strip())


def can_convert(from_unit: str | None, to_unit: str | None, variable: str | None = None) -> bool:
    a, b = normalize_unit(from_unit), normalize_unit(to_unit)
    if a is None or b is None:
        return False
    if a == b:
        return True
    return (a, b) in _GENERIC or (a, b) in _ANALYTE.get(variable or "", {})


def convert(value: float, from_unit: str, to_unit: str, variable: str | None = None) -> float:
    a, b = normalize_unit(from_unit), normalize_unit(to_unit)
    if a is None or b is None:
        raise ValueError("units must not be None")
    if a == b:
        return value
    fn = _GENERIC.get((a, b)) or _ANALYTE.get(variable or "", {}).get((a, b))
    if fn is None:
        raise ValueError(f"no conversion from {a} to {b} for variable {variable!r}")
    return fn(value)


def format_value(value: float, unit: str) -> str:
    decimals = _DECIMALS.get(unit, 2)
    return f"{value:.{decimals}f} {unit}"


def requested_unit(query: str) -> str | None:
    for pattern, unit in _REQUEST_PATTERNS:
        if pattern.search(query):
            return unit
    return None


def parse_value_unit(text: str) -> tuple[float, str] | None:
    """Extract the first ``<number> <unit>`` pair from free text."""
    match = _VALUE_UNIT.search(text)
    if match is None:
        return None
    unit = normalize_unit(match.group("unit"))
    if unit is None:
        return None
    return float(match.group("value")), unit
