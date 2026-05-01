"""Factory: builders compose orchestrator components from settings.

These are unit tests against the build functions individually — they
verify the factory wires the right shapes without requiring Ollama,
Neo4j, Postgres, or Qdrant. The integration test in
`test_integration.py` exercises the full path end-to-end against a
live `docker compose --profile agent` stack.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from noether_memory import InMemoryStore, MemoryStore
from noether_svc_agent.config import AgentSettings
from noether_svc_agent.factory import (
    build_engine,
    build_memory_store,
    build_provider,
    build_tools,
)
from noether_svc_agent.providers import OllamaProvider


def test_build_provider_returns_ollama_for_default_backend() -> None:
    settings = AgentSettings(LLM_BACKEND="ollama", OLLAMA_HOST="http://h:1234", OLLAMA_MODEL="m")
    provider = build_provider(settings)
    assert isinstance(provider, OllamaProvider)


def test_build_provider_raises_for_unwired_cloud_backend() -> None:
    settings = AgentSettings(LLM_BACKEND="openai")  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError, match="not yet wired"):
        build_provider(settings)


def test_build_engine_returns_async_engine_with_asyncpg_driver() -> None:
    """build_engine wires libs/storage's DSN into a working AsyncEngine.

    The exact host/db come from `noether_storage.config.StorageSettings`
    which re-reads .env independently — making host assertions in this
    unit test environment-fragile. The contract this test pins is:
    'build_engine returns an AsyncEngine using the asyncpg driver'. The
    integration test verifies real connectivity.
    """
    settings = AgentSettings()
    engine = build_engine(settings)
    url = str(engine.sync_engine.url)
    assert "postgresql+asyncpg://" in url
    # Default db name from StorageSettings.
    assert "/noether" in url


def test_build_memory_store_falls_back_to_in_memory_on_graphiti_failure() -> None:
    """Neo4j unreachable / Graphiti misconfigured → degrade, don't crash."""
    settings = AgentSettings(NEO4J_URI="bolt://nowhere:7687")

    # Graphiti.connect raises whatever graphiti-core surfaces — we test the
    # fallback by patching connect to throw.
    with patch(
        "noether_memory.graphiti_store.GraphitiStore.connect",
        side_effect=RuntimeError("neo4j unreachable"),
    ):
        store = build_memory_store(settings)

    assert isinstance(store, InMemoryStore)
    # And the returned thing satisfies the MemoryStore Protocol regardless of impl.
    assert isinstance(store, MemoryStore)


def test_build_tools_returns_six_in_canonical_order() -> None:
    """Tool registration order matters for router prompt determinism."""
    settings = AgentSettings()
    engine = build_engine(settings)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))

    tools = build_tools(settings, engine=engine, inference_client=client)
    names = [t.name for t in tools]
    assert names == ["sql", "rag", "multimodal_rag", "forecast", "anomaly", "viz"]


def test_build_tools_uses_injected_inference_client() -> None:
    """Forecast/Anomaly tools share the injected client so a service-level
    pool is reused rather than each tool standing up its own."""
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "request_id": "x",
                "tag": "FT-101",
                "horizon_min": 30,
                "point": 1.0,
                "lower": 0.5,
                "upper": 1.5,
                "model_version": "v",
                "model_kind": "ensemble",
                "latency_ms": 1,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://test")
    settings = AgentSettings(INFERENCE_URL="http://test", INFERENCE_API_KEY="k")
    engine = build_engine(settings)
    tools = build_tools(settings, engine=engine, inference_client=client)

    # Forecast tool — index 3 — should hit the injected mock transport.
    forecast = tools[3]
    from noether_svc_agent.tools import ForecastTagPoint, ForecastToolInput

    out = pytest_run_async(
        forecast.run(
            ForecastToolInput(
                tag="FT-101",
                history=[ForecastTagPoint(ts="2026-04-30T14:00:00Z", value=1.0)],
            )
        )
    )
    assert out.summary
    assert captured == ["/forecast"]


def pytest_run_async(coro):  # type: ignore[no-untyped-def]
    """Run a coroutine to completion in a fresh loop — for non-async test fns."""
    import asyncio

    return asyncio.get_event_loop().run_until_complete(coro)
