"""RagTool / MultimodalRagTool: behaviour shared via base class."""

from __future__ import annotations

import pytest
from noether_rag import RagChunk, RetrievedChunk, SourceType
from noether_svc_agent.tools import MultimodalRagTool, RagTool, RagToolInput


def _hit(
    *,
    doc: str = "doc-a",
    idx: int = 0,
    text: str = "FT-101 calibration step.",
    source_type: str = SourceType.PDF_TEXT,
    score: float = 0.9,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=RagChunk(doc_id=doc, chunk_idx=idx, source_type=source_type, text=text),
        score=score,
    )


@pytest.mark.asyncio
async def test_returns_summary_previews_and_citations() -> None:
    seen: dict[str, object] = {}

    def fake_retrieve(query: str, top_n: int) -> list[RetrievedChunk]:
        seen["query"] = query
        seen["top_n"] = top_n
        return [_hit(doc="manual-1", idx=0), _hit(doc="manual-1", idx=4, score=0.7)]

    tool = RagTool(retrieve_fn=fake_retrieve)
    out = await tool.run(RagToolInput(query="how do I calibrate FT-101?"))

    assert seen["query"] == "how do I calibrate FT-101?"
    assert seen["top_n"] == 5  # default
    # Both chunk_ids surface as citations.
    assert out.citations == ["manual-1:0", "manual-1:4"]
    # Summary previews each hit with its chunk_id prefix.
    assert "[manual-1:0]" in out.summary
    assert "[manual-1:4]" in out.summary
    assert out.data is not None
    assert len(out.data["hits"]) == 2
    assert out.data["hits"][0]["doc_id"] == "manual-1"


@pytest.mark.asyncio
async def test_long_text_is_truncated_in_summary_but_full_in_data() -> None:
    long_text = "x" * 500

    def fake_retrieve(_q: str, _n: int) -> list[RetrievedChunk]:
        return [_hit(text=long_text)]

    tool = RagTool(retrieve_fn=fake_retrieve)
    out = await tool.run(RagToolInput(query="anything"))
    assert "..." in out.summary
    assert len(out.summary) < len(long_text) + 50
    assert out.data is not None
    assert out.data["hits"][0]["text"] == long_text


@pytest.mark.asyncio
async def test_no_hits_path() -> None:
    def fake_retrieve(_q: str, _n: int) -> list[RetrievedChunk]:
        return []

    tool = RagTool(retrieve_fn=fake_retrieve)
    out = await tool.run(RagToolInput(query="nothing matches"))
    assert "No documentation hits" in out.summary
    assert out.citations == []
    assert out.data is not None
    assert out.data["hits"] == []


@pytest.mark.asyncio
async def test_top_n_passed_through() -> None:
    seen: dict[str, int] = {}

    def fake_retrieve(_q: str, top_n: int) -> list[RetrievedChunk]:
        seen["n"] = top_n
        return []

    tool = RagTool(retrieve_fn=fake_retrieve)
    await tool.run(RagToolInput(query="x", top_n=12))
    assert seen["n"] == 12


@pytest.mark.asyncio
async def test_multimodal_tool_distinct_name_and_description() -> None:
    """Router needs distinct names + descriptions to dispatch correctly."""
    text_tool = RagTool(retrieve_fn=lambda q, n: [])
    mm_tool = MultimodalRagTool(retrieve_fn=lambda q, n: [])
    assert text_tool.name == "rag"
    assert mm_tool.name == "multimodal_rag"
    assert text_tool.description != mm_tool.description
    assert "P&ID" in mm_tool.description


@pytest.mark.asyncio
async def test_multimodal_path_surfaces_pid_image_source_type() -> None:
    def fake_retrieve(_q: str, _n: int) -> list[RetrievedChunk]:
        return [_hit(doc="p&id-1", idx=0, source_type=SourceType.PID_IMAGE, text="")]

    tool = MultimodalRagTool(retrieve_fn=fake_retrieve)
    out = await tool.run(RagToolInput(query="show me FT-101 on the P&ID"))
    assert out.citations == ["p&id-1:0"]
    assert out.data is not None
    assert out.data["hits"][0]["source_type"] == SourceType.PID_IMAGE
