"""The zlog z-score: published values, invariances, and the special cases."""

from __future__ import annotations

import math

import pytest

from bench.zlog import (
    SCORE_CAP,
    crps_uniform,
    rating,
    zlog,
    zlog_score,
    zlog_score_truth_range,
)


def test_reference_limits_map_to_plus_minus_1_96() -> None:
    assert zlog(0.8, 0.8, 1.2) == pytest.approx(-1.96)
    assert zlog(1.2, 0.8, 1.2) == pytest.approx(1.96)
    assert zlog(math.sqrt(0.8 * 1.2), 0.8, 1.2) == pytest.approx(0.0)


def test_z_is_the_difference_of_zlog_values() -> None:
    result = zlog_score(1.3, 1.4, lower=0.8, upper=1.2)
    assert result is not None
    assert result.z == pytest.approx(zlog(1.4, 0.8, 1.2) - zlog(1.3, 0.8, 1.2))
    assert result.z == pytest.approx(0.72, abs=0.01)
    assert result.rating == "satisfactory"


@pytest.mark.parametrize(
    ("truth", "answer", "lower", "upper", "z", "expected_rating"),
    [
        (2.6, 2.0, 0.6, 1.2, -1.48, "satisfactory"),  # creatinine, mg/dL
        (132, 138, 135, 145, 2.44, "questionable"),  # sodium, mmol/L
        (39.0, 37.0, 36.5, 37.5, -7.63, "unsatisfactory"),  # temperature, °C
        (8.2, 13.5, 12.0, 16.0, 6.79, "unsatisfactory"),  # haemoglobin, g/dL: anaemia missed
        (250, 250, 150, 400, 0.0, "satisfactory"),  # platelets: the true value itself
    ],
)
def test_worked_examples(
    truth: float, answer: float, lower: float, upper: float, z: float, expected_rating: str
) -> None:
    result = zlog_score(truth, answer, lower=lower, upper=upper)
    assert result is not None
    assert result.z == pytest.approx(z, abs=0.01)
    assert result.rating == expected_rating


def test_score_is_capped_and_unsigned() -> None:
    result = zlog_score(39.0, 37.0, lower=36.5, upper=37.5)
    assert result is not None
    assert result.score == SCORE_CAP
    low = zlog_score(2.6, 2.0, lower=0.6, upper=1.2)
    assert low is not None and low.score == pytest.approx(1.48, abs=0.01)


def test_units_do_not_matter() -> None:
    # Creatinine in mg/dL and in µmol/L (x 88.4), with the reference limits left in mg/dL.
    mg = zlog_score(2.6, 2.0, lower=0.6, upper=1.2)
    umol = zlog_score(2.6 * 88.4, 2.0 * 88.4, lower=0.6, upper=1.2)
    assert mg is not None and umol is not None
    assert mg.z == pytest.approx(umol.z)


def test_over_and_under_by_the_same_ratio_are_equally_far() -> None:
    over = zlog_score(100, 200, lower=70, upper=110)
    under = zlog_score(100, 50, lower=70, upper=110)
    assert over is not None and under is not None
    assert over.z == pytest.approx(-under.z)


def test_error_grows_with_distance() -> None:
    scores = [zlog_score(1.0, a, lower=0.6, upper=1.2) for a in (1.0, 1.1, 1.3, 1.6, 2.0)]
    values = [s.z for s in scores if s is not None]
    assert values == sorted(values) and len(values) == 5


def test_one_sided_range_uses_a_share_of_the_upper_limit() -> None:
    result = zlog_score(250, 100, upper=5)  # C-reactive protein "< 5 mg/L"
    assert result is not None
    assert result.sigma_basis == "one_sided"
    assert result.z == pytest.approx(math.log(100 / 250) / (math.log(5 / 0.75) / 3.92))


def test_no_reference_interval_falls_back_to_a_relative_sd() -> None:
    result = zlog_score(9.6, 10.5)  # outer canthal distance, cm
    assert result is not None
    assert result.sigma_basis == "fallback_relative_sd"
    assert result.z == pytest.approx(math.log(10.5 / 9.6) / 0.15)


def test_values_at_or_below_zero_use_the_linear_scale() -> None:
    result = zlog_score(-8.0, -2.0, lower=-2.0, upper=2.0)  # base excess, mmol/L
    assert result is not None
    assert result.scale == "linear"
    assert result.z == pytest.approx(6.0 / (4.0 / 3.92))
    assert zlog_score(0.0, 5.0) is None


def test_range_answers() -> None:
    point = zlog_score(250, 250, lower=150, upper=400)
    wide = zlog_score(250, 100, 400, lower=150, upper=400)
    narrow = zlog_score(250, 230, 270, lower=150, upper=400)
    missed = zlog_score(250, 400, 500, lower=150, upper=400)
    assert point is not None and wide is not None and narrow is not None and missed is not None
    assert point.score == 0.0
    assert point.score < narrow.score < wide.score < missed.score
    # A range of zero width is a single value.
    assert zlog_score(250, 300, 300, lower=150, upper=400) == zlog_score(
        250, 300, lower=150, upper=400
    )


def test_crps_of_a_uniform_forecast() -> None:
    assert crps_uniform(2.0, 2.0, 0.5) == pytest.approx(1.5)
    assert crps_uniform(-1.0, 1.0, 0.0) == pytest.approx(1 / 6)
    assert crps_uniform(1.0, 3.0, 0.0) == pytest.approx(2.0 - 2 / 6)


def test_rating_limits() -> None:
    assert [rating(z) for z in (0.0, 2.0, 2.5, 3.0, 9.0)] == [
        "satisfactory",
        "satisfactory",
        "questionable",
        "unsatisfactory",
        "unsatisfactory",
    ]


def test_true_value_given_as_a_range_or_a_bound() -> None:
    inside = zlog_score_truth_range(98, 99, 98.5, lower=95, upper=100)
    below = zlog_score_truth_range(98, 99, 92, lower=95, upper=100)
    assert inside is not None and below is not None
    assert inside.score == 0.0
    assert below.z == pytest.approx(math.log(92 / 98) / (math.log(100 / 95) / 3.92))
    # "> 1000": any answer above the bound is right; below it, the distance to the bound counts.
    above = zlog_score_truth_range(1000, None, 2400, lower=140, upper=280)
    short = zlog_score_truth_range(1000, None, 600, lower=140, upper=280)
    assert above is not None and short is not None
    assert above.score == 0.0 and short.z < 0
    # A single true value is the ordinary score; no true value at all has none.
    assert zlog_score_truth_range(2.6, 2.6, 2.0, lower=0.6, upper=1.2) == zlog_score(
        2.6, 2.0, lower=0.6, upper=1.2
    )
    assert zlog_score_truth_range(None, None, 5.0) is None


def test_revised_scale_grows_with_the_true_values_distance_from_normal() -> None:
    # Inside the reference interval nothing changes.
    inside = zlog_score(1.0, 1.1, lower=0.8, upper=1.2, scale_with_truth=True)
    assert inside == zlog_score(1.0, 1.1, lower=0.8, upper=1.2)
    # Haemoglobin 4 g/dL answered as 6.8: both far below 12-16.
    plain = zlog_score(4.0, 6.8, lower=12.0, upper=16.0)
    revised = zlog_score(4.0, 6.8, lower=12.0, upper=16.0, scale_with_truth=True)
    assert plain is not None and revised is not None
    assert plain.score == SCORE_CAP
    factor = abs(zlog(4.0, 12.0, 16.0)) / 3.92
    assert revised.z == pytest.approx(plain.z / factor)
    assert revised.rating == "satisfactory"
    # Missing the abnormality is still a miss.
    missed = zlog_score(4.0, 13.5, lower=12.0, upper=16.0, scale_with_truth=True)
    assert missed is not None and missed.z > revised.z and missed.rating == "unsatisfactory"
    # Without a reference interval there is no distance from normal to scale by.
    assert zlog_score(9.6, 10.5, scale_with_truth=True) == zlog_score(9.6, 10.5)
    # Linear scale (values at or below zero).
    linear = zlog_score(-8.0, -6.0, lower=-2.0, upper=2.0, scale_with_truth=True)
    assert linear is not None and linear.z == pytest.approx(2.0 / (8.0 / 3.92))
