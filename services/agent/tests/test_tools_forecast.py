"""ForecastTool: HTTP shape + ToolResult composition."""

from __future__ import annotations

import json

import httpx
import pytest
from noether_svc_agent.tools import ForecastTagPoint, ForecastTool, ForecastToolInput


def _inference_response() -> dict[str, object]:
    return {
        "request_id": "rid-1",
        "tag": "FT-101",
        "horizon_min": 30,
        "point": 12.5,
        "lower": 11.9,
        "upper": 13.1,
        "model_version": "ensemble-v0",
        "model_kind": "ensemble",
        "latency_ms": 7,
    }


def _tool(handler: httpx.MockTransport) -> ForecastTool:
    client = httpx.AsyncClient(transport=handler, base_url="http://test")
    return ForecastTool(base_url="http://test", api_key="key-123", client=client)


@pytest.mark.asyncio
async def test_posts_history_and_includes_api_key() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_inference_response())

    tool = _tool(httpx.MockTransport(handler))
    out = await tool.run(
        ForecastToolInput(
            tag="FT-101",
            history=[
                ForecastTagPoint(ts="2026-04-30T14:00:00Z", value=12.1),
                ForecastTagPoint(ts="2026-04-30T14:01:00Z", value=12.2),
            ],
        )
    )

    assert captured["url"] == "http://test/forecast"
    assert captured["api_key"] == "key-123"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["tag"] == "FT-101"
    assert len(body["history"]) == 2

    assert "FT-101 forecast" in out.summary
    assert "ensemble" in out.summary
    assert out.data is not None
    assert out.data["point"] == 12.5
    assert out.data["lower"] == 11.9
    assert out.data["upper"] == 13.1


@pytest.mark.asyncio
async def test_inference_503_propagates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "no model yet"})

    tool = _tool(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await tool.run(
            ForecastToolInput(
                tag="FT-101",
                history=[ForecastTagPoint(ts="2026-04-30T14:00:00Z", value=12.1)],
            )
        )
