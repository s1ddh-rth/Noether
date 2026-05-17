"""POST /chat — request/response shape, auth, and orchestrator wiring."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from noether_svc_agent.app import build_app
from noether_svc_agent.routers.chat import get_graph


def _final_state(**overrides: Any) -> dict[str, Any]:
    """Default ChatState dict the (mocked) graph returns."""
    base: dict[str, Any] = {
        "selected_tools": ["sql"],
        "tool_results": [],
        "answer": "FT-101 is at 12.3.",
        "citations": [],
        "vega_spec": None,
        "facts_written": 0,
    }
    base.update(overrides)
    return base


def _client_with_fake_graph(graph: Any) -> TestClient:
    app = build_app()
    app.dependency_overrides[get_graph] = lambda: graph
    return TestClient(app)


def test_chat_returns_orchestrator_state_fields() -> None:
    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(
        return_value=_final_state(
            selected_tools=["sql", "rag"],
            answer="FT-101 alert was a calibration drift [doc-1:0].",
            citations=["doc-1:0"],
            facts_written=2,
        )
    )
    client = _client_with_fake_graph(fake_graph)

    resp = client.post(
        "/chat",
        json={"session_id": "sess-A", "question": "Why did anomaly fire?"},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "sess-A"
    assert body["answer"] == "FT-101 alert was a calibration drift [doc-1:0]."
    assert body["citations"] == ["doc-1:0"]
    assert body["selected_tools"] == ["sql", "rag"]
    assert body["facts_written"] == 2
    assert body["vega_spec"] is None

    # And the graph was driven with the right input.
    fake_graph.ainvoke.assert_awaited_once()
    call_args = fake_graph.ainvoke.await_args
    assert call_args.args[0] == {
        "session_id": "sess-A",
        "question": "Why did anomaly fire?",
    }


def test_chat_passes_through_vega_spec_when_present() -> None:
    spec = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json"}
    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(return_value=_final_state(vega_spec=spec))
    client = _client_with_fake_graph(fake_graph)

    resp = client.post(
        "/chat",
        json={"session_id": "s", "question": "show me FT-101"},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.json()["vega_spec"] == spec


def test_chat_rejects_missing_api_key() -> None:
    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(return_value=_final_state())
    client = _client_with_fake_graph(fake_graph)

    resp = client.post("/chat", json={"session_id": "s", "question": "q"})
    assert resp.status_code == 401
    fake_graph.ainvoke.assert_not_awaited()


def test_chat_rejects_wrong_api_key() -> None:
    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(return_value=_final_state())
    client = _client_with_fake_graph(fake_graph)

    resp = client.post(
        "/chat",
        json={"session_id": "s", "question": "q"},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 401


def test_chat_returns_503_when_graph_not_initialised() -> None:
    """Without dependency override, the lifespan-less app has no graph."""
    app = build_app()
    client = TestClient(app)
    resp = client.post(
        "/chat",
        json={"session_id": "s", "question": "q"},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.status_code == 503
    assert "not initialised" in resp.json()["detail"]


def test_chat_validates_request_shape() -> None:
    fake_graph = AsyncMock()
    client = _client_with_fake_graph(fake_graph)

    # Empty question
    resp = client.post(
        "/chat",
        json={"session_id": "s", "question": ""},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.status_code == 422

    # Empty session_id
    resp = client.post(
        "/chat",
        json={"session_id": "", "question": "q"},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.status_code == 422

    # Question too long (> 4000 chars)
    resp = client.post(
        "/chat",
        json={"session_id": "s", "question": "x" * 5000},
        headers={"X-API-Key": "changeme-please"},
    )
    assert resp.status_code == 422


def test_healthz_still_works() -> None:
    """Adding chat router shouldn't have broken the meta endpoints."""
    app = build_app()
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
