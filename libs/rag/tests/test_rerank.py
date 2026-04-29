from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
from noether_rag.models import RagChunk, SourceType
from noether_rag.rerank import BgeReranker, Reranker


def _chunk(idx: int, text: str) -> RagChunk:
    return RagChunk(doc_id="d", chunk_idx=idx, source_type=SourceType.PDF_TEXT, text=text)


class _StubReranker:
    """Returns chunks scored by their length — purely to exercise the protocol."""

    def rerank(
        self, query: str, chunks: list[RagChunk], top_n: int
    ) -> list[tuple[RagChunk, float]]:
        scored = [(c, float(len(c.text))) for c in chunks]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]


def test_stub_satisfies_reranker_protocol() -> None:
    r: Reranker = _StubReranker()
    chunks = [_chunk(0, "short"), _chunk(1, "much longer chunk text")]
    out = r.rerank("q", chunks, top_n=1)
    assert len(out) == 1
    assert out[0][0].chunk_idx == 1


def test_bge_reranker_constructs_cross_encoder_with_cache() -> None:
    fake_ce = MagicMock()
    fake_ce.predict.return_value = np.array([0.1, 0.9])
    with patch("noether_rag.rerank.CrossEncoder", return_value=fake_ce) as m:
        BgeReranker(model_name="BAAI/bge-reranker-base", cache_folder="/m")
        m.assert_called_once_with("BAAI/bge-reranker-base", cache_dir="/m")


def test_bge_reranker_orders_by_score_and_caps_at_top_n() -> None:
    fake_ce = MagicMock()
    # third chunk gets the highest score
    fake_ce.predict.return_value = np.array([0.2, 0.5, 0.9])
    with (
        patch("noether_rag.rerank.CrossEncoder", return_value=fake_ce),
        patch.dict("os.environ", {"RAG_MODEL_DIR": "/tmp/m"}, clear=False),
    ):
        r = BgeReranker()
        chunks = [_chunk(0, "a"), _chunk(1, "b"), _chunk(2, "c")]
        out = r.rerank("q", chunks, top_n=2)
        assert [c.chunk_idx for c, _ in out] == [2, 1]
        assert [round(s, 1) for _, s in out] == [0.9, 0.5]
        # CrossEncoder is fed (query, chunk.text) pairs in input order
        pairs = fake_ce.predict.call_args.args[0]
        assert pairs == [("q", "a"), ("q", "b"), ("q", "c")]


def test_bge_reranker_empty_input_returns_empty() -> None:
    fake_ce = MagicMock()
    with patch("noether_rag.rerank.CrossEncoder", return_value=fake_ce):
        r = BgeReranker()
        assert r.rerank("q", [], top_n=5) == []
        fake_ce.predict.assert_not_called()
