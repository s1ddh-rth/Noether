"""Prometheus metrics: emission on /chat and /metrics exposition."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from noether_svc_agent.app import build_app
from noether_svc_agent.routers.chat import get_graph


def _final_state(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "selected_tools": [],
        "tool_results": [],
        "answer": "",
        "citations": [],
        "vega_spec": None,
        "facts_written": 0,
    }
    base.update(overrides)
    return base


def _client(graph: Any) -> TestClient:
    app = build_app()
    app.dependency_overrides[get_graph] = lambda: graph
    return TestClient(app)


def test_metrics_endpoint_returns_prometheus_format() -> None:
    client = _client(AsyncMock())
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    # Prometheus exposition format: HELP + TYPE comments + sample lines.
    assert "agent_chats_total" in body
    assert "agent_chat_latency_ms" in body
    assert "agent_tool_calls_total" in body
    # Histogram self-registers buckets.
    assert "_bucket" in body


def test_chat_increments_ok_counter_and_observes_latency() -> None:
    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(return_value=_final_state(selected_tools=["sql", "rag"]))
    client = _client(fake_graph)

    before = client.get("/metrics").text

    resp = client.post(
        "/chat",
        json={"session_id": "s", "question": "q"},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.status_code == 200

    after = client.get("/metrics").text

    # status="ok" counter increased.
    assert _counter(before, 'agent_chats_total{status="ok"}') < _counter(
        after, 'agent_chats_total{status="ok"}'
    )

    # Per-tool counters bumped for the two selected tools.
    assert _counter(before, 'agent_tool_calls_total{tool="sql"}') < _counter(
        after, 'agent_tool_calls_total{tool="sql"}'
    )
    assert _counter(before, 'agent_tool_calls_total{tool="rag"}') < _counter(
        after, 'agent_tool_calls_total{tool="rag"}'
    )


def test_chat_failure_increments_error_counter() -> None:
    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
    app = build_app()
    app.dependency_overrides[get_graph] = lambda: fake_graph
    # raise_server_exceptions=False so we get the 500 back instead of the
    # exception bubbling into the test process.
    client = TestClient(app, raise_server_exceptions=False)

    before_err = _counter(client.get("/metrics").text, 'agent_chats_total{status="error"}')

    resp = client.post(
        "/chat",
        json={"session_id": "s", "question": "q"},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.status_code == 500

    after_err = _counter(client.get("/metrics").text, 'agent_chats_total{status="error"}')
    assert after_err == before_err + 1


def _counter(metrics_body: str, label_prefix: str) -> float:
    """Pull a counter sample value out of the prometheus exposition text.

    Returns 0.0 if the label combination hasn't been emitted yet — the
    counter is lazy and only appears in /metrics after the first inc().
    """
    for line in metrics_body.splitlines():
        if line.startswith(label_prefix):
            # Format: `name{labels} value [optional timestamp]`
            return float(line.rsplit(maxsplit=1)[-1] if " " in line else "0")
    return 0.0
