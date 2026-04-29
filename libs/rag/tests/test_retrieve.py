from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.models import RagChunk, RetrievedChunk, SourceType
from noether_rag.retrieve import retrieve
from qdrant_client import QdrantClient

FloatArray = npt.NDArray[np.float32]


class _StubEmbedder:
    """Vector-encodes by reusing the chunk_idx of any chunk whose text matches."""

    dim = 8

    def __init__(self, vectors: dict[str, FloatArray]) -> None:
        # dict from text -> vector (so a query reuses the same vector as a known chunk)
        self.vectors = vectors

    def encode(self, texts: list[str]) -> FloatArray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            if t in self.vectors:
                out[i] = self.vectors[t]
            else:
                # arbitrary unique-ish vector
                rng = np.random.default_rng(abs(hash(t)) % (2**32))
                out[i] = rng.standard_normal(self.dim).astype(np.float32)
        return out


class _IdentityReranker:
    """Returns chunks in input order, scoring each by 1/(rank+1)."""

    def rerank(
        self, query: str, chunks: list[RagChunk], top_n: int
    ) -> list[tuple[RagChunk, float]]:
        return [(c, 1.0 / (i + 1)) for i, c in enumerate(chunks[:top_n])]


@pytest.fixture
def fitted_indexes() -> tuple[QdrantIndex, Bm25Index, _StubEmbedder, list[RagChunk]]:
    chunks = [
        RagChunk(
            doc_id="d",
            chunk_idx=0,
            source_type=SourceType.PDF_TEXT,
            text="Flow transmitter FT-101 reading was normal.",
        ),
        RagChunk(
            doc_id="d",
            chunk_idx=1,
            source_type=SourceType.PDF_TEXT,
            text="Pump P-203 trip causes downstream pressure drop.",
        ),
        RagChunk(
            doc_id="d",
            chunk_idx=2,
            source_type=SourceType.PDF_TEXT,
            text="FT-101 calibration drifted by 0.4% last month.",
        ),
        RagChunk(
            doc_id="d",
            chunk_idx=3,
            source_type=SourceType.PDF_TEXT,
            text="Tower T-001 packing inspection scheduled for Q2.",
        ),
    ]
    rng = np.random.default_rng(0)
    vecs = rng.standard_normal((4, 8)).astype(np.float32)
    embedder = _StubEmbedder(vectors={c.text: vecs[i] for i, c in enumerate(chunks)})

    qi = QdrantIndex(client=QdrantClient(":memory:"), collection="test")
    qi.ensure_collection(dim=8)
    qi.upsert(chunks, vecs)

    bm = Bm25Index()
    bm.fit(chunks)

    return qi, bm, embedder, chunks


def test_retrieve_returns_retrieved_chunks(
    fitted_indexes: tuple[QdrantIndex, Bm25Index, _StubEmbedder, list[RagChunk]],
) -> None:
    qi, bm, embedder, chunks = fitted_indexes
    # Use chunk 2's text as the query so dense lookup finds chunk 2 first.
    out = retrieve(
        chunks[2].text,
        embedder=embedder,
        qdrant_indexes=[qi],
        bm25_index=bm,
        reranker=_IdentityReranker(),
        top_n=3,
    )
    assert len(out) == 3
    assert all(isinstance(r, RetrievedChunk) for r in out)


def test_retrieve_top_n_caps_results(
    fitted_indexes: tuple[QdrantIndex, Bm25Index, _StubEmbedder, list[RagChunk]],
) -> None:
    qi, bm, embedder, _ = fitted_indexes
    out = retrieve(
        "FT-101",
        embedder=embedder,
        qdrant_indexes=[qi],
        bm25_index=bm,
        reranker=_IdentityReranker(),
        top_n=2,
    )
    assert len(out) <= 2


def test_retrieve_finds_relevant_chunks_via_bm25_when_dense_is_random(
    fitted_indexes: tuple[QdrantIndex, Bm25Index, _StubEmbedder, list[RagChunk]],
) -> None:
    qi, bm, embedder, _ = fitted_indexes
    # Query has no known dense vector match; BM25 carries the day on FT-101.
    out = retrieve(
        "FT-101 calibration",
        embedder=embedder,
        qdrant_indexes=[qi],
        bm25_index=bm,
        reranker=_IdentityReranker(),
        top_n=4,
    )
    chunk_indices = [r.chunk.chunk_idx for r in out]
    # chunks 0 and 2 mention FT-101 and must appear in the result set
    assert 2 in chunk_indices
    assert 0 in chunk_indices


def test_retrieve_works_without_reranker(
    fitted_indexes: tuple[QdrantIndex, Bm25Index, _StubEmbedder, list[RagChunk]],
) -> None:
    qi, bm, embedder, _ = fitted_indexes
    out = retrieve(
        "FT-101",
        embedder=embedder,
        qdrant_indexes=[qi],
        bm25_index=bm,
        reranker=None,
        top_n=3,
    )
    assert 1 <= len(out) <= 3
    # scores fall back to RRF fused score (always positive)
    assert all(r.score > 0 for r in out)


def test_retrieve_accepts_multiple_qdrant_collections(
    fitted_indexes: tuple[QdrantIndex, Bm25Index, _StubEmbedder, list[RagChunk]],
) -> None:
    """Phase 2 multimodal path will pass two Qdrant indexes here unchanged."""
    qi, bm, embedder, chunks = fitted_indexes

    qi2 = QdrantIndex(client=QdrantClient(":memory:"), collection="test2")
    qi2.ensure_collection(dim=8)
    rng = np.random.default_rng(1)
    qi2.upsert(chunks, rng.standard_normal((4, 8)).astype(np.float32))

    out = retrieve(
        "FT-101",
        embedder=embedder,
        qdrant_indexes=[qi, qi2],
        bm25_index=bm,
        reranker=_IdentityReranker(),
        top_n=2,
    )
    assert len(out) == 2
