from __future__ import annotations

from pathlib import Path

import pytest
from noether_rag.index import Bm25Index
from noether_rag.models import RagChunk, SourceType


def _chunk(idx: int, text: str) -> RagChunk:
    return RagChunk(
        doc_id="doc",
        chunk_idx=idx,
        source_type=SourceType.PDF_TEXT,
        text=text,
    )


CORPUS = [
    _chunk(0, "Flow transmitter FT-101 reads 25.3 GPM."),
    _chunk(1, "Pump P-203 trip causes downstream pressure drop."),
    _chunk(2, "Tower T-001 packing inspection scheduled for Q2."),
    _chunk(3, "FT-101 calibration drifted by 0.4% last month."),
]


class TestBm25Search:
    def test_empty_index_returns_empty(self) -> None:
        idx = Bm25Index()
        idx.fit([])
        assert idx.search("anything", k=5) == []

    def test_query_for_known_token_returns_matching_chunk_first(self) -> None:
        idx = Bm25Index()
        idx.fit(CORPUS)
        hits = idx.search("FT-101 calibration", k=4)
        assert len(hits) == 4
        # both chunks 0 and 3 mention FT-101; chunk 3 also mentions
        # "calibration" — it should rank ahead of chunk 0.
        top_chunk, _ = hits[0]
        assert top_chunk.chunk_idx == 3

    def test_zero_token_query_returns_empty(self) -> None:
        idx = Bm25Index()
        idx.fit(CORPUS)
        # punctuation-only query — tokenizer yields nothing
        assert idx.search("!!!", k=5) == []

    def test_k_caps_results(self) -> None:
        idx = Bm25Index()
        idx.fit(CORPUS)
        hits = idx.search("pump tower flow", k=2)
        assert len(hits) == 2


class TestBm25Persistence:
    def test_save_and_load_roundtrip_preserves_search_results(self, tmp_path: Path) -> None:
        idx = Bm25Index()
        idx.fit(CORPUS)
        before = idx.search("FT-101 calibration", k=4)

        path = tmp_path / "_bm25.pkl"
        idx.save(path)
        assert path.exists()

        reloaded = Bm25Index.load(path)
        after = reloaded.search("FT-101 calibration", k=4)

        assert [c.chunk_id for c, _ in before] == [c.chunk_id for c, _ in after]

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Bm25Index.load(tmp_path / "nope.pkl")
