"""Smoke tests for the agent service scaffold."""

from __future__ import annotations

from fastapi.testclient import TestClient
from noether_svc_agent.app import build_app


def test_healthz_returns_ok() -> None:
    client = TestClient(build_app())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_app_carries_settings_on_state() -> None:
    app = build_app()
    assert app.state.settings is not None
    # Defaults match config.py — guards against accidental drift.
    assert app.state.settings.llm_backend == "ollama"
    assert app.state.settings.offline_mode is True


def test_module_level_app_is_a_fastapi_instance() -> None:
    """`app` exists at module top-level so uvicorn can import it directly."""
    from fastapi import FastAPI
    from noether_svc_agent.app import app

    assert isinstance(app, FastAPI)
