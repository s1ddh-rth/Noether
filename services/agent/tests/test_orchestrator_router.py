"""RouterNode: LLM-as-classifier with malformed-JSON resilience."""

from __future__ import annotations

import pytest
from noether_svc_agent.orchestrator import RouterNode
from noether_svc_agent.providers import MockProvider
from noether_svc_agent.tools import (
    AnomalyTool,
    ForecastTool,
    MultimodalRagTool,
    RagTool,
    SqlTool,
    VizTool,
)
from sqlalchemy.ext.asyncio import AsyncEngine


def _all_tools() -> list[object]:
    """The six tools, instantiated cheaply (no real engine, no real retrieve)."""

    class _FakeEngine:
        pass

    fake_engine: AsyncEngine = _FakeEngine()  # type: ignore[assignment]
    return [
        SqlTool(fake_engine),
        RagTool(retrieve_fn=lambda q, n: []),
        MultimodalRagTool(retrieve_fn=lambda q, n: []),
        ForecastTool(base_url="http://test", api_key="k"),
        AnomalyTool(base_url="http://test", api_key="k"),
        VizTool(),
    ]


@pytest.mark.asyncio
async def test_picks_forecast_tool_for_forecast_question() -> None:
    provider = MockProvider(responses=['{"tools": ["forecast"]}'])
    router = RouterNode(provider=provider, tools=_all_tools())  # type: ignore[arg-type]

    out = await router.select_tools("What will FT-101 be in 30 minutes?")
    assert out == ["forecast"]
    # And the LLM was asked in json_mode.
    assert provider.calls[0].json_mode is True


@pytest.mark.asyncio
async def test_picks_anomaly_plus_rag_for_why_question() -> None:
    provider = MockProvider(responses=['{"tools": ["anomaly", "rag"]}'])
    router = RouterNode(provider=provider, tools=_all_tools())  # type: ignore[arg-type]

    out = await router.select_tools("Why did anomaly fire on FT-101 yesterday at 14:23?")
    assert out == ["anomaly", "rag"]


@pytest.mark.asyncio
async def test_filters_out_unknown_tool_names() -> None:
    """LLM hallucinates a tool that isn't registered → drop it."""
    provider = MockProvider(responses=['{"tools": ["sql", "made_up_tool"]}'])
    router = RouterNode(provider=provider, tools=_all_tools())  # type: ignore[arg-type]

    out = await router.select_tools("What's FT-101?")
    assert out == ["sql"]


@pytest.mark.asyncio
async def test_caps_at_max_tools() -> None:
    provider = MockProvider(responses=['{"tools": ["sql", "rag", "forecast", "anomaly", "viz"]}'])
    router = RouterNode(provider=provider, tools=_all_tools(), max_tools=3)  # type: ignore[arg-type]

    out = await router.select_tools("everything")
    assert len(out) == 3
    assert out == ["sql", "rag", "forecast"]


@pytest.mark.asyncio
async def test_strips_code_fences() -> None:
    """Local LLMs love adding ```json fences``` even when told not to."""
    provider = MockProvider(responses=['```json\n{"tools": ["sql"]}\n```'])
    router = RouterNode(provider=provider, tools=_all_tools())  # type: ignore[arg-type]

    out = await router.select_tools("FT-101 now?")
    assert out == ["sql"]


@pytest.mark.asyncio
async def test_retries_once_on_malformed_then_succeeds() -> None:
    provider = MockProvider(
        responses=[
            "I think you should call sql, but here's some extra prose.",
            '{"tools": ["sql"]}',
        ]
    )
    router = RouterNode(provider=provider, tools=_all_tools())  # type: ignore[arg-type]

    out = await router.select_tools("FT-101 now?")
    assert out == ["sql"]
    # Two LLM calls; second one carries the stricter system message.
    assert len(provider.calls) == 2
    assert provider.calls[1].messages[0].role == "system"
    assert "valid JSON" in provider.calls[1].messages[0].content


@pytest.mark.asyncio
async def test_falls_back_to_sql_after_two_malformed_responses() -> None:
    provider = MockProvider(
        responses=[
            "narrative response 1",
            "still narrative",
        ]
    )
    router = RouterNode(provider=provider, tools=_all_tools())  # type: ignore[arg-type]

    out = await router.select_tools("anything")
    # Better to answer narrowly than not at all — sql is the safe default.
    assert out == ["sql"]


@pytest.mark.asyncio
async def test_fallback_drops_when_sql_not_registered() -> None:
    """If sql isn't even in the registered tool set, fall through to empty."""
    provider = MockProvider(responses=["bad", "still bad"])
    # Only viz registered.
    router = RouterNode(provider=provider, tools=[VizTool()])  # type: ignore[list-item]

    out = await router.select_tools("anything")
    assert out == []


@pytest.mark.asyncio
async def test_rejects_non_dict_json() -> None:
    """`["sql"]` is parseable JSON but not the expected shape."""
    provider = MockProvider(
        responses=[
            '["sql"]',  # raw list, not {"tools": [...]}
            '{"tools": ["sql"]}',
        ]
    )
    router = RouterNode(provider=provider, tools=_all_tools())  # type: ignore[arg-type]

    out = await router.select_tools("x")
    # Retry handled it.
    assert out == ["sql"]
