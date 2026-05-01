"""ParamExtractor: LLM-driven JSON → validated tool input model."""

from __future__ import annotations

import pytest
from noether_svc_agent.orchestrator import ParamExtractor
from noether_svc_agent.providers import MockProvider
from noether_svc_agent.tools import RagTool, RagToolInput, VizTool


@pytest.mark.asyncio
async def test_extracts_valid_input_against_schema() -> None:
    provider = MockProvider(responses=['{"query": "FT-101 calibration", "top_n": 3}'])
    extractor = ParamExtractor(provider=provider)
    tool = RagTool(retrieve_fn=lambda q, n: [])

    out = await extractor.extract(tool, "How do I calibrate FT-101?")
    assert isinstance(out, RagToolInput)
    assert out.query == "FT-101 calibration"
    assert out.top_n == 3


@pytest.mark.asyncio
async def test_returns_none_on_unparseable_json() -> None:
    provider = MockProvider(responses=["this is not JSON"])
    extractor = ParamExtractor(provider=provider)
    tool = RagTool(retrieve_fn=lambda q, n: [])

    out = await extractor.extract(tool, "anything")
    assert out is None


@pytest.mark.asyncio
async def test_returns_none_when_validation_fails() -> None:
    """Schema validation rejects bad payloads — fan-out skips this tool."""
    provider = MockProvider(responses=['{"query": ""}'])  # empty query violates min_length=1
    extractor = ParamExtractor(provider=provider)
    tool = RagTool(retrieve_fn=lambda q, n: [])

    out = await extractor.extract(tool, "anything")
    assert out is None


@pytest.mark.asyncio
async def test_strips_code_fences() -> None:
    provider = MockProvider(responses=['```json\n{"query": "ok"}\n```'])
    extractor = ParamExtractor(provider=provider)
    tool = RagTool(retrieve_fn=lambda q, n: [])

    out = await extractor.extract(tool, "x")
    assert isinstance(out, RagToolInput)
    assert out.query == "ok"


@pytest.mark.asyncio
async def test_prompt_carries_schema_and_question() -> None:
    provider = MockProvider(responses=['{"query": "x"}'])
    extractor = ParamExtractor(provider=provider)
    tool = VizTool()

    await extractor.extract(tool, "plot FT-101 over the last 5 minutes")
    sent = provider.calls[0].messages[0].content
    # The schema for VizToolInput names the tool's fields.
    assert "title" in sent
    assert "series" in sent
    assert "plot FT-101 over the last 5 minutes" in sent
    # And we asked for json_mode.
    assert provider.calls[0].json_mode is True
