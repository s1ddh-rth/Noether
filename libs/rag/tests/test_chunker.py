from __future__ import annotations

from noether_rag.chunker import chunk_text


def test_empty_input_returns_empty_list() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n  \n") == []


def test_short_text_returns_single_chunk() -> None:
    text = "hello world"
    chunks = chunk_text(text, size=2000, overlap=200)
    assert chunks == [text]


def test_each_chunk_respects_size_bound() -> None:
    # 50 paragraphs * ~80 chars each = ~4000 chars
    paragraphs = [f"Paragraph {i}: " + ("x" * 60) for i in range(50)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, size=500, overlap=50)
    assert all(len(c) <= 500 for c in chunks)
    assert len(chunks) > 1


def test_chunks_overlap_when_text_exceeds_size() -> None:
    from itertools import pairwise

    paragraphs = [f"Paragraph {i}: " + ("x" * 60) for i in range(50)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, size=500, overlap=50)

    # Adjacent chunks must share *some* content. We don't require the
    # overlap to be exactly N chars (separators may shift the boundary)
    # but consecutive chunks must have a common prefix/suffix to support
    # context preservation across boundaries.
    for prev, nxt in pairwise(chunks):
        prev_tail = prev[-50:]
        # at least one non-whitespace token from prev_tail must appear in nxt
        prev_tokens = {t for t in prev_tail.split() if t}
        nxt_tokens = set(nxt.split())
        assert prev_tokens & nxt_tokens, (
            f"no token overlap between adjacent chunks:\n"
            f"prev tail: {prev_tail!r}\nnext head: {nxt[:80]!r}"
        )


def test_no_chunk_loses_atomic_paragraphs() -> None:
    # Every paragraph should appear at least once across all chunks.
    paragraphs = [f"P{i}_unique_token_{i}" for i in range(20)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, size=200, overlap=20)
    joined = "\n".join(chunks)
    for p in paragraphs:
        assert p in joined


def test_extreme_long_unbreakable_token_falls_back_to_hard_split() -> None:
    # No separators present, single ultra-long word.
    text = "a" * 2500
    chunks = chunk_text(text, size=500, overlap=0)
    assert all(len(c) <= 500 for c in chunks)
    assert "".join(chunks) == text  # nothing lost


def test_default_size_is_about_500_tokens() -> None:
    # Documented default: ~500 tokens ≈ 2000 chars (4 chars/token).
    from noether_rag.chunker import DEFAULT_OVERLAP, DEFAULT_SIZE

    assert DEFAULT_SIZE == 2000
    assert DEFAULT_OVERLAP == 200
