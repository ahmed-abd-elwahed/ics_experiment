"""Cluster bootstrap confidence intervals and Cohen's kappa."""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Estimate:
    mean: float | None
    low: float | None
    high: float | None
    n: int

    def fmt(self, digits: int = 2, pct: bool = False) -> str:
        if self.mean is None:
            return "–"
        scale, suffix = (100.0, "%") if pct else (1.0, "")
        body = f"{self.mean * scale:.{0 if pct else digits}f}{suffix}"
        if self.low is None or self.high is None or self.n < 2:
            return body
        lo, hi = self.low * scale, self.high * scale
        return f"{body} [{lo:.{0 if pct else digits}f}, {hi:.{0 if pct else digits}f}]"


def cluster_bootstrap(
    values: Sequence[tuple[str, float]], *, n_boot: int = 2000, seed: int = 0
) -> Estimate:
    """Mean with a 95% percentile interval, resampling whole clusters (here: diagnoses).

    Questions about the same diagnosis are not independent, so clusters, not questions, are
    resampled.
    """
    if not values:
        return Estimate(None, None, None, 0)
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for cluster, value in values:
        sums[cluster] += value
        counts[cluster] += 1
    clusters = list(sums)
    mean = sum(sums.values()) / sum(counts.values())
    if len(clusters) < 2:
        return Estimate(mean, None, None, len(values))
    rng = random.Random(seed)
    draws = []
    for _ in range(n_boot):
        picked = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        total = sum(counts[c] for c in picked)
        draws.append(sum(sums[c] for c in picked) / total)
    draws.sort()
    low = draws[int(0.025 * (n_boot - 1))]
    high = draws[int(0.975 * (n_boot - 1))]
    return Estimate(mean, low, high, len(values))


def cohen_kappa(
    a: Sequence[int | str], b: Sequence[int | str], *, weights: str | None = None
) -> float | None:
    """Cohen's kappa; ``weights`` "linear" or "quadratic" for ordinal integer grades."""
    if len(a) != len(b) or not a:
        return None
    labels = sorted(set(a) | set(b), key=str)
    index = {label: i for i, label in enumerate(labels)}
    k = len(labels)
    if k == 1:
        return 1.0
    n = len(a)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        observed[index[x]][index[y]] += 1 / n
    row = [sum(r) for r in observed]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]

    def weight(i: int, j: int) -> float:
        if weights is None:
            return 0.0 if i == j else 1.0
        if not all(isinstance(label, int) for label in labels):
            raise ValueError("weighted kappa needs integer grades")
        span = float(max(labels) - min(labels)) or 1.0  # type: ignore[operator]
        d = abs(float(labels[i]) - float(labels[j])) / span
        return d if weights == "linear" else d * d

    disagree_obs = sum(weight(i, j) * observed[i][j] for i in range(k) for j in range(k))
    disagree_exp = sum(weight(i, j) * row[i] * col[j] for i in range(k) for j in range(k))
    if disagree_exp == 0:
        return 1.0
    return 1 - disagree_obs / disagree_exp
