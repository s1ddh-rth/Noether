from __future__ import annotations

import pytest
from noether_rag.fusion import rrf


def test_single_ranking_returns_canonical_scores() -> None:
    fused = rrf([["a", "b", "c"]], k=60)
    assert [item for item, _ in fused] == ["a", "b", "c"]
    expected = [1 / 61, 1 / 62, 1 / 63]
    actual = [score for _, score in fused]
    assert actual == pytest.approx(expected, rel=1e-9)


def test_overlap_combines_two_rankings() -> None:
    rankings = [
        ["a", "b", "c"],
        ["b", "a", "d"],
    ]
    fused = dict(rrf(rankings, k=60))
    # a appears at rank 1 in A and rank 2 in B
    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)
    # b appears at rank 2 in A and rank 1 in B → same total as a
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
    # c appears only in A at rank 3
    assert fused["c"] == pytest.approx(1 / 63)
    # d appears only in B at rank 3
    assert fused["d"] == pytest.approx(1 / 63)


def test_results_sorted_descending() -> None:
    rankings = [["x", "y", "z"], ["z", "y"]]
    fused = rrf(rankings, k=60)
    scores = [s for _, s in fused]
    assert scores == sorted(scores, reverse=True)


def test_k_parameter_changes_scores() -> None:
    fused_k10 = rrf([["a"]], k=10)
    fused_k60 = rrf([["a"]], k=60)
    assert fused_k10[0][1] == pytest.approx(1 / 11)
    assert fused_k60[0][1] == pytest.approx(1 / 61)


def test_empty_rankings_return_empty_list() -> None:
    assert rrf([], k=60) == []
    assert rrf([[], []], k=60) == []


def test_default_k_is_sixty() -> None:
    # Sanity-check the documented default — design.md fixes it at 60.
    fused = rrf([["a"]])
    assert fused[0][1] == pytest.approx(1 / 61)


def test_works_with_arbitrary_hashable_items() -> None:
    rankings = [
        [("doc_1", 0), ("doc_1", 1)],
        [("doc_2", 0), ("doc_1", 0)],
    ]
    fused = rrf(rankings, k=60)
    items = [it for it, _ in fused]
    # ("doc_1", 0) appears in both rankings — ranks ahead of singletons.
    assert items[0] == ("doc_1", 0)
