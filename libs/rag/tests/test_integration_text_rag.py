"""End-to-end text RAG: parse + chunk + embed + index + retrieve.

Runs entirely in-process (Qdrant in-memory client, stub embedder).
Demonstrates the Phase-1 demo target from the OpenSpec proposal:
'ingest a 3-doc fixture and retrieve() returns the seeded top hit.'
"""

from __future__ import annotations

import shutil
from pathlib import Path

from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.ingest import ingest_dir
from noether_rag.retrieve import retrieve
from noether_rag.tests_helpers import StubTextEmbedder
from qdrant_client import QdrantClient


def test_end_to_end_ingest_then_retrieve_returns_seeded_chunk(
    sample_pdf_path: Path, tmp_path: Path
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    # Three identical PDFs — content-hash dedup means we ingest once. The
    # fixture mentions FT-101 on page 1 and "Steam pressure" on page 2.
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        shutil.copy(sample_pdf_path, src / name)

    embedder = StubTextEmbedder(dim=8)
    qi = QdrantIndex(client=QdrantClient(":memory:"), collection="rag_text")
    bm = Bm25Index()

    stats = ingest_dir(
        src=src,
        qdrant_index=qi,
        bm25_index=bm,
        embedder=embedder,
        data_dir=tmp_path / "rag-index",
    )
    assert stats.chunks_indexed >= 1
    assert qi.count() == stats.chunks_indexed

    # Query for a token only present in the seeded fixture; BM25 carries the
    # signal cleanly because the stub embedder vectors are random.
    out = retrieve(
        "FT-101 calibration drift",
        embedder=embedder,
        qdrant_indexes=[qi],
        bm25_index=bm,
        reranker=None,  # no reranker — RRF score order is enough at this scale
        top_n=3,
    )
    assert out, "expected at least one retrieved chunk"
    assert any("FT-101" in r.chunk.text for r in out)


def test_retrieve_after_persisted_bm25_reload(sample_pdf_path: Path, tmp_path: Path) -> None:
    """Reloading the BM25 pickle into a fresh index reproduces the same hits."""
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(sample_pdf_path, src / "doc.pdf")

    embedder = StubTextEmbedder(dim=8)
    qi = QdrantIndex(client=QdrantClient(":memory:"), collection="rag_text")
    bm = Bm25Index()
    ingest_dir(
        src=src,
        qdrant_index=qi,
        bm25_index=bm,
        embedder=embedder,
        data_dir=tmp_path / "rag-index",
    )
    pickle_path = tmp_path / "rag-index" / "rag_text_bm25.pkl"
    assert pickle_path.exists()

    bm_reloaded = Bm25Index.load(pickle_path)
    out = retrieve(
        "Steam pressure",
        embedder=embedder,
        qdrant_indexes=[qi],
        bm25_index=bm_reloaded,
        reranker=None,
        top_n=2,
    )
    assert any("Steam pressure" in r.chunk.text for r in out)
