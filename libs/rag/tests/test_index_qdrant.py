from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest
from noether_rag.index import QdrantIndex
from noether_rag.models import RagChunk, SourceType
from qdrant_client import QdrantClient

FloatArray = npt.NDArray[np.float32]


@pytest.fixture
def index() -> QdrantIndex:
    return QdrantIndex(client=QdrantClient(":memory:"), collection="test_text")


def _chunks(n: int) -> list[RagChunk]:
    return [
        RagChunk(
            doc_id=f"doc_{i % 3}",
            chunk_idx=i,
            source_type=SourceType.PDF_TEXT,
            text=f"chunk {i} content",
            metadata={"page": i % 5 + 1},
        )
        for i in range(n)
    ]


def _vecs(n: int, dim: int = 8) -> FloatArray:
    rng = np.random.default_rng(42)
    return rng.standard_normal((n, dim)).astype(np.float32)


class TestEnsureCollection:
    def test_creates_when_missing(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        assert index.client.collection_exists(index.collection)

    def test_is_idempotent(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        index.ensure_collection(dim=8)  # must not raise


class TestUpsertAndSearch:
    def test_upsert_then_count(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        chunks, vecs = _chunks(5), _vecs(5)
        index.upsert(chunks, vecs)
        assert index.count() == 5

    def test_upsert_is_idempotent_per_chunk(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        chunks, vecs = _chunks(3), _vecs(3)
        index.upsert(chunks, vecs)
        # re-upsert same chunks: count unchanged
        index.upsert(chunks, vecs)
        assert index.count() == 3

    def test_search_returns_chunks_and_scores(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        chunks, vecs = _chunks(10), _vecs(10)
        index.upsert(chunks, vecs)

        # query with the vector of chunk 3 — that chunk should be the top hit
        hits = index.search(query_vec=vecs[3], k=3)
        assert len(hits) == 3
        top_chunk, _top_score = hits[0]
        assert isinstance(top_chunk, RagChunk)
        assert top_chunk.chunk_id == chunks[3].chunk_id
        # all returned scores must be floats
        assert all(isinstance(s, float) for _, s in hits)

    def test_search_preserves_metadata(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        chunks, vecs = _chunks(3), _vecs(3)
        index.upsert(chunks, vecs)
        hits = index.search(query_vec=vecs[0], k=1)
        chunk, _ = hits[0]
        assert chunk.metadata == {"page": 1}
        assert chunk.source_type == SourceType.PDF_TEXT


class TestUpsertValidation:
    def test_mismatched_chunks_and_vectors_raises(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        with pytest.raises(ValueError, match="length"):
            index.upsert(_chunks(3), _vecs(2))

    def test_empty_upsert_is_noop(self, index: QdrantIndex) -> None:
        index.ensure_collection(dim=8)
        index.upsert([], np.zeros((0, 8), dtype=np.float32))
        assert index.count() == 0
