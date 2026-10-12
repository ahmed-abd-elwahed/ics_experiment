"""The zlog z-score: how far an answer's value is from the true value, on a common scale.

Two published methods combined:

- the zlog transformation (Hoffmann et al. 2017) maps a result ``x`` to a z-score on a log scale
  from the variable's reference limits alone, so that the reference interval is always
  -1.96 to +1.96: ``zlog(x) = (ln x - (ln LL + ln UL) / 2) * 3.92 / (ln UL - ln LL)``;
- the proficiency-testing z-score (ISO 13528) grades a result by its distance from an assigned
  value over a set standard deviation: ``z = (x - x_assigned) / sigma``.

Here the assigned value is the hidden true value and both values are on the zlog scale, so
``z = zlog(answer) - zlog(truth) = (ln answer - ln truth) / sigma`` with
``sigma = (ln UL - ln LL) / 3.92``. Only the ratio UL / LL enters, so the reference limits may
be in any unit; the answer and the true value must share one.

Everything here is arithmetic: no LLM calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Width of a 95% reference interval in standard deviations (2 x 1.96).
INTERVAL_SDS = 3.92
# ISO 13528 limits: |z| <= 2 satisfactory, |z| >= 3 unsatisfactory (action signal).
SATISFACTORY = 2.0
UNSATISFACTORY = 3.0
# The score is |z| capped at the unsatisfactory limit; unanswered questions get the cap.
SCORE_CAP = UNSATISFACTORY
# A one-sided reference range ("< 5") has no lower limit: it is taken as this share of the upper.
ONE_SIDED_LOWER_SHARE = 0.15
# Without any reference interval, the standard deviation is this share of the value (log scale).
FALLBACK_RELATIVE_SD = 0.15


@dataclass(frozen=True)
class ZlogScore:
    z: float  # signed for a single value; the (non-negative) CRPS for a range
    score: float  # |z| capped at SCORE_CAP; lower is better
    rating: str  # satisfactory | questionable | unsatisfactory
    scale: str  # log | linear
    sigma_basis: str  # reference_interval | one_sided | fallback_relative_sd


def zlog(x: float, lower: float, upper: float) -> float:
    """Hoffmann's zlog value of ``x`` for the reference interval ``lower``-``upper``."""
    if not (x > 0 and 0 < lower < upper):
        raise ValueError("zlog needs x > 0 and 0 < lower < upper")
    mid = (math.log(lower) + math.log(upper)) / 2
    return (math.log(x) - mid) * INTERVAL_SDS / (math.log(upper) - math.log(lower))


def rating(abs_z: float) -> str:
    if abs_z <= SATISFACTORY:
        return "satisfactory"
    return "questionable" if abs_z < UNSATISFACTORY else "unsatisfactory"


def crps_uniform(low: float, high: float, observed: float) -> float:
    """Continuous ranked probability score of a uniform forecast on ``low``-``high``.

    It is the absolute error when ``low == high`` (Gneiting and Raftery 2007).
    """
    if high < low:
        low, high = high, low
    width = high - low
    if width == 0:
        return abs(low - observed)
    if low <= observed <= high:
        mean_abs = ((observed - low) ** 2 + (high - observed) ** 2) / (2 * width)
    else:
        mean_abs = abs((low + high) / 2 - observed)
    return mean_abs - width / 6


def zlog_score(
    truth: float,
    answer_low: float,
    answer_high: float | None = None,
    *,
    lower: float | None = None,
    upper: float | None = None,
    scale_with_truth: bool = False,
) -> ZlogScore | None:
    """Score an answer (a value, or a range ``answer_low``-``answer_high``) against ``truth``.

    ``lower`` and ``upper`` are the variable's reference limits for this patient. Returns None
    when no scale can be set: a value at or below zero without a two-sided reference interval.

    ``scale_with_truth`` (the revised score): the standard deviation grows with the true
    value's own distance from the middle of the reference interval, by the factor
    ``max(1, |zlog(truth)| / 3.92)``. ISO 13528 lets the standard deviation for proficiency
    assessment depend on the level of the assigned value; here an error is judged against the
    healthy spread for a true value near the reference interval, and against the true
    value's own deviation for one far outside it (more than 3.92 on the zlog scale), so a very
    abnormal true value answered with a similarly abnormal one is no longer scored like a
    miss. An answer in the middle of the reference interval then scores 3.92, never
    satisfactory, however abnormal the true value is.
    """
    high = answer_low if answer_high is None else answer_high
    low, high = min(answer_low, high), max(answer_low, high)
    two_sided = lower is not None and upper is not None and lower < upper
    log_scale = truth > 0 and low > 0

    if log_scale:
        if two_sided and lower is not None and upper is not None and lower > 0:
            sigma = (math.log(upper) - math.log(lower)) / INTERVAL_SDS
            basis = "reference_interval"
        elif upper is not None and upper > 0:
            sigma = -math.log(ONE_SIDED_LOWER_SHARE) / INTERVAL_SDS
            basis = "one_sided"
        else:
            sigma = FALLBACK_RELATIVE_SD
            basis = "fallback_relative_sd"
        if scale_with_truth and basis != "fallback_relative_sd":
            middle = (
                (math.log(lower) + math.log(upper)) / 2
                if basis == "reference_interval" and lower is not None and upper is not None
                else math.log(upper * math.sqrt(ONE_SIDED_LOWER_SHARE))  # type: ignore[operator]
            )
            sigma *= max(1.0, abs(math.log(truth) - middle) / sigma / INTERVAL_SDS)
        z_low, z_high = math.log(low / truth) / sigma, math.log(high / truth) / sigma
    else:
        # Values at or below zero (base excess, a change from baseline) have no logarithm.
        if not (two_sided and lower is not None and upper is not None):
            return None
        sigma = (upper - lower) / INTERVAL_SDS
        basis = "reference_interval"
        if scale_with_truth:
            sigma *= max(1.0, abs(truth - (lower + upper) / 2) / sigma / INTERVAL_SDS)
        z_low, z_high = (low - truth) / sigma, (high - truth) / sigma

    z = z_low if z_low == z_high else crps_uniform(z_low, z_high, 0.0)
    return ZlogScore(
        z=z,
        score=min(abs(z), SCORE_CAP),
        rating=rating(abs(z)),
        scale="log" if log_scale else "linear",
        sigma_basis=basis,
    )


def zlog_score_truth_range(
    truth_low: float | None,
    truth_high: float | None,
    answer_low: float,
    answer_high: float | None = None,
    *,
    lower: float | None = None,
    upper: float | None = None,
    scale_with_truth: bool = False,
) -> ZlogScore | None:
    """As :func:`zlog_score`, for a true value given as a range or a bound.

    ``None`` is an open side ("> 1000" is ``truth_low=1000, truth_high=None``). An answer inside
    the true range scores 0; outside it, its distance to the nearest end counts. An answer
    given as a range is taken at its midpoint (geometric when positive).
    """
    if truth_low is None and truth_high is None:
        return None
    if truth_low is not None and truth_low == truth_high:
        return zlog_score(
            truth_low, answer_low, answer_high, lower=lower, upper=upper,
            scale_with_truth=scale_with_truth,
        )  # fmt: skip
    high = answer_low if answer_high is None else answer_high
    low, high = min(answer_low, high), max(answer_low, high)
    point = math.sqrt(low * high) if low > 0 else (low + high) / 2
    if truth_low is not None and point < truth_low:
        nearest = truth_low
    elif truth_high is not None and point > truth_high:
        nearest = truth_high
    else:
        nearest = point
    return zlog_score(nearest, point, lower=lower, upper=upper, scale_with_truth=scale_with_truth)
