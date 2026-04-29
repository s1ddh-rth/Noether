from __future__ import annotations

import pytest
from noether_rag.models import PageText, RagChunk, RetrievedChunk
from pydantic import ValidationError


class TestRagChunk:
    def test_valid_construction(self) -> None:
        chunk = RagChunk(
            doc_id="abc123",
            chunk_idx=0,
            source_type="pdf_text",
            text="hello world",
        )
        assert chunk.doc_id == "abc123"
        assert chunk.chunk_idx == 0
        assert chunk.source_type == "pdf_text"
        assert chunk.text == "hello world"
        assert chunk.metadata == {}

    def test_metadata_defaults_empty(self) -> None:
        chunk = RagChunk(doc_id="d", chunk_idx=0, source_type="pdf_text", text="t")
        assert chunk.metadata == {}
        # default factory must produce a fresh dict per instance
        chunk.metadata["page"] = 1
        chunk2 = RagChunk(doc_id="d", chunk_idx=1, source_type="pdf_text", text="t")
        assert chunk2.metadata == {}

    def test_metadata_accepts_arbitrary_payload(self) -> None:
        chunk = RagChunk(
            doc_id="d",
            chunk_idx=0,
            source_type="pid_image",  # Phase 2 source type — model is open
            text="caption",
            metadata={"page": 3, "bbox": [0, 0, 100, 100], "image_path": "p.png"},
        )
        assert chunk.metadata["page"] == 3
        assert chunk.metadata["bbox"] == [0, 0, 100, 100]

    def test_empty_doc_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RagChunk(doc_id="", chunk_idx=0, source_type="pdf_text", text="t")

    def test_empty_source_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RagChunk(doc_id="d", chunk_idx=0, source_type="", text="t")

    def test_negative_chunk_idx_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RagChunk(doc_id="d", chunk_idx=-1, source_type="pdf_text", text="t")

    def test_chunk_id_is_doc_idx_pair(self) -> None:
        chunk = RagChunk(doc_id="abc", chunk_idx=7, source_type="pdf_text", text="t")
        assert chunk.chunk_id == "abc:7"

    def test_point_uuid_is_stable_and_unique(self) -> None:
        a = RagChunk(doc_id="d", chunk_idx=0, source_type="pdf_text", text="t")
        b = RagChunk(doc_id="d", chunk_idx=0, source_type="pdf_text", text="DIFFERENT")
        c = RagChunk(doc_id="d", chunk_idx=1, source_type="pdf_text", text="t")
        # point_uuid is derived only from (doc_id, chunk_idx) — re-ingesting
        # the same chunk with edited text must overwrite the same Qdrant point.
        assert a.point_uuid == b.point_uuid
        assert a.point_uuid != c.point_uuid


class TestPageText:
    def test_valid(self) -> None:
        p = PageText(page_number=1, text="hello")
        assert p.page_number == 1

    def test_page_number_is_one_indexed(self) -> None:
        with pytest.raises(ValidationError):
            PageText(page_number=0, text="hello")


class TestRetrievedChunk:
    def test_wraps_chunk_with_score(self) -> None:
        chunk = RagChunk(doc_id="d", chunk_idx=0, source_type="pdf_text", text="t")
        rc = RetrievedChunk(chunk=chunk, score=0.87)
        assert rc.chunk is chunk
        assert rc.score == pytest.approx(0.87)
