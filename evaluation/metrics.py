"""Ranking metrics for a differential against one true diagnosis.

The same metrics, with the same definitions, as ranx computes for one relevant item per query:
hit_rate@k is 1 when the true code is among the first k, mrr is 1/rank, and ndcg@10 is
1/log2(rank + 1) within the first ten (the ideal ranking scores 1).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

HIT_RATE_AT = tuple(range(1, 11))
METRICS = (*(f"hit_rate@{k}" for k in HIT_RATE_AT), "ndcg@10", "mrr")


def ranked_codes(predictions: Sequence[tuple[str, float]]) -> list[str]:
    """Codes by descending score. A code predicted twice keeps its highest score, uncoded
    predictions ("") are dropped, and equal scores keep the order they were given in."""
    best: dict[str, float] = {}
    for code, score in predictions:
        if code and (code not in best or score > best[code]):
            best[code] = score
    return sorted(best, key=lambda code: -best[code])  # stable


def rank_of(truth: str, codes: Sequence[str]) -> int | None:
    """The 1-based position of the true code; None if it is absent or the truth has no code."""
    if not truth or truth not in codes:
        return None
    return codes.index(truth) + 1


def case_scores(rank: int | None) -> dict[str, float]:
    scores = {f"hit_rate@{k}": float(rank is not None and rank <= k) for k in HIT_RATE_AT}
    scores["ndcg@10"] = 1 / math.log2(rank + 1) if rank is not None and rank <= 10 else 0.0
    scores["mrr"] = 1 / rank if rank is not None else 0.0
    return scores


def mean_scores(ranks: Sequence[int | None]) -> dict[str, float]:
    """Each metric averaged over the cases; a case without a hit counts as zero."""
    if not ranks:
        return dict.fromkeys(METRICS, 0.0)
    per_case = [case_scores(rank) for rank in ranks]
    return {m: sum(s[m] for s in per_case) / len(per_case) for m in METRICS}
