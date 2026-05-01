"""FastAPI app construction for the agent service.

`build_app()` wires routes + settings; the heavy LLM / Postgres / Neo4j
factory runs in the lifespan handler so unit tests can use the app
without standing up backends. Tests substitute the graph via
`app.dependency_overrides[get_graph]` (see `routers/chat.py`).

The lifespan is best-effort: if the factory fails (Neo4j down, model
not pulled, etc.) we log + leave `app.state.graph = None`. /chat then
returns 503 with a clear message — the meta endpoints (/healthz,
/metrics) keep serving so operators / dashboards aren't taken down by
a backend hiccup.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from noether_ingest.logging import configure  # type: ignore[import-untyped]

from noether_svc_agent.config import AgentSettings
from noether_svc_agent.factory import build_engine, build_memory_store, build_orchestrator
from noether_svc_agent.routers import chat as chat_router
from noether_svc_agent.routers import health as health_router
from noether_svc_agent.routers import metrics as metrics_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: AgentSettings = app.state.settings

    engine = None
    inference_client = None
    try:
        engine = build_engine(settings)
        inference_client = httpx.AsyncClient(timeout=120.0)
        memory_store = build_memory_store(settings)
        graph = build_orchestrator(
            settings,
            engine=engine,
            inference_client=inference_client,
            memory_store=memory_store,
        )
        app.state.graph = graph
        app.state.engine = engine
        app.state.inference_client = inference_client
        logger.info("agent.lifespan.ready")
    except Exception:
        logger.exception("agent.lifespan.factory_failed")
        app.state.graph = None
        if inference_client is not None:
            await inference_client.aclose()
        if engine is not None:
            await engine.dispose()

    try:
        yield
    finally:
        if app.state.__dict__.get("inference_client") is not None:
            await app.state.inference_client.aclose()
        if app.state.__dict__.get("engine") is not None:
            await app.state.engine.dispose()


def build_app() -> FastAPI:
    settings = AgentSettings()
    configure(settings.log_level, service="agent")

    app = FastAPI(
        title="Noether Agent",
        version="0.1.0",
        description="LangGraph-orchestrated /chat over plant data, RAG, and forecasts.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.graph = None  # filled by lifespan; keeps /chat's get_graph happy on TestClient
    app.include_router(health_router.router)
    app.include_router(metrics_router.router)
    app.include_router(chat_router.router)
    return app


app = build_app()
