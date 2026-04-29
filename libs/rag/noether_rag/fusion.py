"""Reciprocal Rank Fusion.

Canonical formula (Cormack, Clarke & Buettcher, 2009):

    score(d) = sum over rankings r of 1 / (k + rank_r(d))

Rank is 1-indexed (top result = rank 1). The default `k=60` is the value
fixed in `add-rag-pipeline/design.md` and is reused unchanged for the
multimodal collection merge in Phase 2.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from typing import TypeVar

T = TypeVar("T", bound=Hashable)


def rrf(rankings: Sequence[Sequence[T]], k: int = 60) -> list[tuple[T, float]]:
    """Fuse multiple ranked result lists into one descending-score list."""
    fused: dict[T, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            fused[item] = fused.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
