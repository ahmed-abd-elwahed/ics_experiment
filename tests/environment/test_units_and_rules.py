from __future__ import annotations

import pytest

from medsim import rules, units


@pytest.mark.parametrize(
    ("value", "src", "dst", "variable", "expected"),
    [
        (37.0, "°C", "°F", None, 98.6),
        (98.6, "F", "celsius", None, 37.0),
        (70.0, "kg", "lbs", None, 154.32),
        (180.0, "mg/dL", "mmol/L", "glucose", 9.99),
        (1.0, "mg/dL", "umol/L", "creatinine", 88.42),
        (12.5, "g/dL", "g/L", None, 125.0),
    ],
)
def test_convert(value: float, src: str, dst: str, variable: str | None, expected: float) -> None:
    assert units.convert(value, src, dst, variable) == pytest.approx(expected, abs=0.01)


def test_molar_conversion_requires_analyte() -> None:
    assert not units.can_convert("mg/dL", "mmol/L")
    with pytest.raises(ValueError):
        units.convert(100.0, "mg/dL", "mmol/L")


def test_requested_unit_and_parse() -> None:
    assert units.requested_unit("What is the temperature in Fahrenheit?") == "°F"
    assert units.requested_unit("glucose in mmol/L please") == "mmol/L"
    assert units.requested_unit("What is the temperature?") is None
    assert units.parse_value_unit("Temperature is 38.1 °C.") == (38.1, "°C")
    assert units.parse_value_unit("no numbers here") is None


def test_normalize_query_strips_filler() -> None:
    assert rules.normalize_query("What is the patient's temperature?") == "temperature"
    assert rules.normalize_query("temperature") == "temperature"


def test_canonical_variable_and_timepoint() -> None:
    assert rules.canonical_variable("What's her pulse?") == "heart_rate"
    assert rules.canonical_variable("SpO2 on room air?") == "oxygen_saturation"
    assert rules.canonical_variable("pulse ox reading") == "oxygen_saturation"
    assert rules.canonical_variable("temperature and heart rate") is None
    assert rules.timepoint("temperature on day 3") == "day3"
    assert rules.timepoint("lactate 48 hours after admission") == "hour48"
    assert rules.timepoint("temperature at admission") == "admission"
    assert rules.timepoint("temperature") is None


def test_split_multipart() -> None:
    assert rules.split_multipart("What are the patient's temperature and heart rate?") == [
        "What are the patient's temperature?",
        "What are the patient's heart rate?",
    ]
    assert rules.split_multipart("temperature, heart rate and blood pressure on day 3?") == [
        "temperature on day 3?",
        "heart rate on day 3?",
        "blood pressure on day 3?",
    ]


@pytest.mark.parametrize(
    "query",
    [
        "Does the patient have chest pain and shortness of breath?",
        "What is the temperature?",
        "What is the temperature and why?",
    ],
)
def test_split_multipart_leaves_single_questions(query: str) -> None:
    assert rules.split_multipart(query) == [query]
