"""Multimodal retrieve: text query → text RAG + P&ID image collections via RRF.

Exercises the Phase-2 design point: each Qdrant collection can carry its
own query embedder, so the OpenCLIP image collection is queried with the
OpenCLIP text encoder while the BGE text collection is queried with
`BgeTextEmbedder` — both merge through the existing RRF unchanged.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.ingest import ingest_dir, ingest_dir_multimodal
from noether_rag.retrieve import retrieve
import numpy as np
import numpy.typing as npt
from PIL import Image

from noether_rag.tests_helpers import StubTextEmbedder

_FloatArray = npt.NDArray[np.float32]
from qdrant_client import QdrantClient


class _SharedSpaceEmbedder:
    """Stub satisfying both `Embedder` (text) and `ImageEmbedder` (image)
    Protocols and steering both encoders towards a fixed `anchor` vector.

    With both methods returning the same vector for any input, a text
    query lands on every indexed image — exactly the behaviour we need
    to prove the cross-modal plumbing works without loading OpenCLIP.
    """

    def __init__(self, dim: int, anchor: _FloatArray) -> None:
        self._dim = dim
        self._anchor = anchor.astype(np.float32)

    @property
    def dim(self) -> int:
        return self._dim

    def encode_image(self, images: list[Image.Image]) -> _FloatArray:
        if not images:
            return np.zeros((0, self._dim), dtype=np.float32)
        return np.tile(self._anchor, (len(images), 1))

    def encode(self, texts: list[str]) -> _FloatArray:
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        return np.tile(self._anchor, (len(texts), 1))


def test_text_query_finds_pid_image_via_cross_modal_embedder(
    sample_pdf_path: Path, tmp_path: Path
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(sample_pdf_path, src / "doc.pdf")

    # Anchor vector that both text and image encoders steer to in this test.
    rng = np.random.default_rng(42)
    anchor = rng.standard_normal(8).astype(np.float32)
    anchor /= np.linalg.norm(anchor)

    # Image-side: dedicated multimodal embedder + Qdrant collection.
    mm_emb = _SharedSpaceEmbedder(dim=8, anchor=anchor)
    mm_qi = QdrantIndex(client=QdrantClient(":memory:"), collection="mm_test")
    ingest_dir_multimodal(src=src, qdrant_index=mm_qi, image_embedder=mm_emb)
    assert mm_qi.count() == 2  # 2 pages

    # Text-side: BGE-style embedder + Qdrant collection (Phase-1 path).
    text_emb = StubTextEmbedder(dim=8)
    text_qi = QdrantIndex(client=QdrantClient(":memory:"), collection="text_test")
    bm = Bm25Index()
    ingest_dir(
        src=src,
        qdrant_index=text_qi,
        bm25_index=bm,
        embedder=text_emb,
        data_dir=tmp_path / "rag-index",
    )
    assert text_qi.count() >= 1

    # Query: pass each collection with its native embedder. retrieve()
    # encodes the same query with each, then RRF-merges.
    out = retrieve(
        "FT-101 calibration",
        embedder=text_emb,  # default for plain-QdrantIndex entries
        qdrant_indexes=[
            text_qi,  # plain entry → uses default `embedder`
            (mm_qi, mm_emb),  # tuple entry → uses mm_emb for query
        ],
        bm25_index=bm,
        reranker=None,
        top_n=5,
    )
    assert out, "expected hits from at least one collection"
    sources = {r.chunk.source_type for r in out}
    # The cross-modal path must surface a P&ID image hit.
    assert "pid_image" in sources


def test_backward_compat_phase1_signature_still_works(
    sample_pdf_path: Path, tmp_path: Path
) -> None:
    """Phase-1 callers passing a bare `list[QdrantIndex]` continue to work."""
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(sample_pdf_path, src / "doc.pdf")

    text_emb = StubTextEmbedder(dim=8)
    text_qi = QdrantIndex(client=QdrantClient(":memory:"), collection="text_only")
    bm = Bm25Index()
    ingest_dir(
        src=src,
        qdrant_index=text_qi,
        bm25_index=bm,
        embedder=text_emb,
        data_dir=tmp_path / "rag-index",
    )
    out = retrieve(
        "FT-101",
        embedder=text_emb,
        qdrant_indexes=[text_qi],
        bm25_index=bm,
        reranker=None,
        top_n=3,
    )
    assert out
    assert all(r.chunk.source_type == "pdf_text" for r in out)
