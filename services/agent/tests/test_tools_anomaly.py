"""AnomalyTool: /anomaly + optional /explain composition."""

from __future__ import annotations

import httpx
import pytest
from noether_svc_agent.tools import AnomalyTool, AnomalyToolInput


def _score_body(*, alert: bool = True) -> dict[str, object]:
    return {
        "request_id": "rid-2",
        "score": 0.83,
        "detectors": {"iforest": 0.71, "mahalanobis": 0.83, "ewma": 0.42},
        "tags": ["FT-101", "FT-102"],
        "alert": alert,
        "latency_ms": 12,
    }


def _explain_body() -> dict[str, object]:
    return {
        "alert_id": "abc",
        "score": 0.83,
        "contributions": [
            {"tag": "FT-101", "contribution": 0.51},
            {"tag": "FT-102", "contribution": 0.22},
            {"tag": "FT-103", "contribution": 0.10},
        ],
    }


def _tool(handler: httpx.MockTransport) -> AnomalyTool:
    client = httpx.AsyncClient(transport=handler, base_url="http://test")
    return AnomalyTool(base_url="http://test", api_key="key-xyz", client=client)


@pytest.mark.asyncio
async def test_score_only_path_no_explain_call() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=_score_body(alert=False))

    tool = _tool(httpx.MockTransport(handler))
    out = await tool.run(
        AnomalyToolInput(
            tags=["FT-101", "FT-102"],
            start="2026-04-30T14:23:00Z",
            end="2026-04-30T14:24:00Z",
        )
    )
    assert seen == ["/anomaly"]
    assert "ok" in out.summary
    assert out.data is not None
    assert "explain" not in out.data


@pytest.mark.asyncio
async def test_include_explain_calls_both_endpoints() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/anomaly":
            return httpx.Response(200, json=_score_body(alert=True))
        return httpx.Response(200, json=_explain_body())

    tool = _tool(httpx.MockTransport(handler))
    out = await tool.run(
        AnomalyToolInput(
            tags=["FT-101"],
            start="2026-04-30T14:23:00Z",
            end="2026-04-30T14:24:00Z",
            alert_id="abc",
            include_explain=True,
        )
    )
    assert seen == ["/anomaly", "/explain"]
    assert "ALERT" in out.summary
    assert "FT-101=0.510" in out.summary
    assert out.data is not None
    assert "explain" in out.data


@pytest.mark.asyncio
async def test_include_explain_without_alert_id_skips_explain_call() -> None:
    """Guard: include_explain=True but alert_id=None should not 400 /explain."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=_score_body(alert=True))

    tool = _tool(httpx.MockTransport(handler))
    out = await tool.run(
        AnomalyToolInput(
            tags=["FT-101"],
            start="2026-04-30T14:23:00Z",
            end="2026-04-30T14:24:00Z",
            include_explain=True,
            alert_id=None,
        )
    )
    assert seen == ["/anomaly"]
    assert out.data is not None
    assert "explain" not in out.data
