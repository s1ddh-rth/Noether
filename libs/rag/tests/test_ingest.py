from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.ingest import IngestStats, ingest_dir
from noether_rag.tests_helpers import StubTextEmbedder
from qdrant_client import QdrantClient


@pytest.fixture
def src_dir(sample_pdf_path: Path, tmp_path: Path) -> Path:
    """Build a 3-PDF source directory by copying the embedded fixture."""
    src = tmp_path / "src"
    src.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        shutil.copy(sample_pdf_path, src / name)
    return src


@pytest.fixture
def fresh_indexes() -> tuple[QdrantIndex, Bm25Index, StubTextEmbedder]:
    qi = QdrantIndex(client=QdrantClient(":memory:"), collection="ingest_test")
    bm = Bm25Index()
    embedder = StubTextEmbedder(dim=8)
    qi.ensure_collection(dim=embedder.dim)
    return qi, bm, embedder


class TestIngestDir:
    def test_dedups_identical_files_in_same_run(
        self,
        src_dir: Path,
        fresh_indexes: tuple[QdrantIndex, Bm25Index, StubTextEmbedder],
        tmp_path: Path,
    ) -> None:
        """Three byte-identical PDFs share a SHA → one logical doc."""
        qi, bm, embedder = fresh_indexes
        stats = ingest_dir(
            src=src_dir,
            qdrant_index=qi,
            bm25_index=bm,
            embedder=embedder,
            data_dir=tmp_path / "rag-index",
        )
        assert stats.docs_processed == 1
        assert stats.docs_skipped == 2
        assert stats.chunks_indexed >= 1
        # Qdrant got every chunk we said we indexed.
        assert qi.count() == stats.chunks_indexed
        pickle_path = tmp_path / "rag-index" / "ingest_test_bm25.pkl"
        assert pickle_path.exists()

    def test_doc_id_is_content_sha256(
        self,
        src_dir: Path,
        fresh_indexes: tuple[QdrantIndex, Bm25Index, StubTextEmbedder],
        tmp_path: Path,
    ) -> None:
        qi, bm, embedder = fresh_indexes
        ingest_dir(
            src=src_dir,
            qdrant_index=qi,
            bm25_index=bm,
            embedder=embedder,
            data_dir=tmp_path / "rag-index",
        )
        doc_ids = {c.doc_id for c in bm._chunks}
        assert len(doc_ids) == 1
        # The doc_id is a 64-char hex SHA-256 digest.
        only_id = next(iter(doc_ids))
        assert len(only_id) == 64
        int(only_id, 16)  # decodes as hex

    def test_idempotent_rerun(
        self,
        src_dir: Path,
        fresh_indexes: tuple[QdrantIndex, Bm25Index, StubTextEmbedder],
        tmp_path: Path,
    ) -> None:
        qi, bm, embedder = fresh_indexes
        first = ingest_dir(
            src=src_dir,
            qdrant_index=qi,
            bm25_index=bm,
            embedder=embedder,
            data_dir=tmp_path / "rag-index",
        )
        second = ingest_dir(
            src=src_dir,
            qdrant_index=qi,
            bm25_index=bm,
            embedder=embedder,
            data_dir=tmp_path / "rag-index",
        )
        # Every input file matched a known SHA → nothing new processed.
        assert second.docs_processed == 0
        assert second.docs_skipped == 3  # one per input file in src/
        # The total indexed-chunk count is stable.
        assert second.chunks_indexed == first.chunks_indexed
        assert qi.count() == first.chunks_indexed

    def test_reindex_flag_drops_prior_state(
        self,
        src_dir: Path,
        fresh_indexes: tuple[QdrantIndex, Bm25Index, StubTextEmbedder],
        tmp_path: Path,
    ) -> None:
        qi, bm, embedder = fresh_indexes
        ingest_dir(
            src=src_dir,
            qdrant_index=qi,
            bm25_index=bm,
            embedder=embedder,
            data_dir=tmp_path / "rag-index",
        )
        again = ingest_dir(
            src=src_dir,
            qdrant_index=qi,
            bm25_index=bm,
            embedder=embedder,
            data_dir=tmp_path / "rag-index",
            reindex=True,
        )
        # With reindex=True we ignore the prior pickle, so the first
        # unique file is reprocessed; the other two still de-dup in-run.
        assert again.docs_processed == 1
        assert again.docs_skipped == 2


class TestIngestStats:
    def test_stats_dataclass_shape(self) -> None:
        s = IngestStats(docs_processed=2, docs_skipped=1, chunks_indexed=5)
        assert s.docs_processed == 2
        assert s.docs_skipped == 1
        assert s.chunks_indexed == 5
