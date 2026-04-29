from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from noether_rag.index import QdrantIndex
from noether_rag.ingest import ingest_dir_multimodal
from noether_rag.models import SourceType
from noether_rag.tests_helpers import StubImageEmbedder
from qdrant_client import QdrantClient


@pytest.fixture
def src_dir(sample_pdf_path: Path, tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    for name in ("a.pdf", "b.pdf"):
        shutil.copy(sample_pdf_path, src / name)
    return src


@pytest.fixture
def fresh_index() -> tuple[QdrantIndex, StubImageEmbedder]:
    qi = QdrantIndex(client=QdrantClient(":memory:"), collection="ingest_mm_test")
    embedder = StubImageEmbedder(dim=8)
    qi.ensure_collection(dim=embedder.dim)
    return qi, embedder


class TestMultimodalIngest:
    def test_emits_one_chunk_per_page(
        self,
        src_dir: Path,
        fresh_index: tuple[QdrantIndex, StubImageEmbedder],
    ) -> None:
        qi, embedder = fresh_index
        stats = ingest_dir_multimodal(src=src_dir, qdrant_index=qi, image_embedder=embedder)
        # 2 byte-identical PDFs dedup to 1 logical doc; doc has 2 pages.
        assert stats.docs_processed == 1
        assert stats.docs_skipped == 1
        assert stats.chunks_indexed == 2

    def test_chunks_carry_pid_image_source_type(
        self,
        src_dir: Path,
        fresh_index: tuple[QdrantIndex, StubImageEmbedder],
    ) -> None:
        qi, embedder = fresh_index
        ingest_dir_multimodal(src=src_dir, qdrant_index=qi, image_embedder=embedder)
        # Use any vector to retrieve all points; we just want to inspect payload.
        from PIL import Image

        probe_vec = embedder.encode_image([Image.new("RGB", (10, 10))])[0]
        hits = qi.search(query_vec=probe_vec, k=10)
        assert len(hits) == 2
        for chunk, _ in hits:
            assert chunk.source_type == SourceType.PID_IMAGE
            assert "page" in chunk.metadata
            assert "filename" in chunk.metadata

    def test_idempotent_rerun(
        self,
        src_dir: Path,
        fresh_index: tuple[QdrantIndex, StubImageEmbedder],
    ) -> None:
        qi, embedder = fresh_index
        first = ingest_dir_multimodal(src=src_dir, qdrant_index=qi, image_embedder=embedder)
        second = ingest_dir_multimodal(src=src_dir, qdrant_index=qi, image_embedder=embedder)
        assert second.docs_processed == 0
        assert second.docs_skipped == 2
        assert qi.count() == first.chunks_indexed

    def test_empty_directory_is_noop(
        self,
        tmp_path: Path,
        fresh_index: tuple[QdrantIndex, StubImageEmbedder],
    ) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        qi, embedder = fresh_index
        stats = ingest_dir_multimodal(src=empty, qdrant_index=qi, image_embedder=embedder)
        assert stats.docs_processed == 0
        assert stats.chunks_indexed == 0
        assert qi.count() == 0
