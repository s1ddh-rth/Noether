"""FastAPI app construction for the agent service.

`build_app()` wires routes + settings; the heavy LLM/Qdrant/Neo4j
factory runs in the lifespan handler so unit tests can use the app
without standing up backends. Tests substitute the graph via
`app.dependency_overrides[get_graph]` (see `routers/chat.py`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from noether_ingest.logging import configure  # type: ignore[import-untyped]

from noether_svc_agent.config import AgentSettings
from noether_svc_agent.routers import chat as chat_router
from noether_svc_agent.routers import health as health_router
from noether_svc_agent.routers import metrics as metrics_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Production wire-up of the orchestrator (provider + tools + memory +
    # graph) lives here. For v0.1 the factory is intentionally not built —
    # /chat returns 503 until a graph is attached. The integration test
    # PR wires it up; unit tests override `get_graph` via FastAPI's
    # dependency_overrides so they don't need the factory at all.
    yield


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
    app.include_router(health_router.router)
    app.include_router(metrics_router.router)
    app.include_router(chat_router.router)
    return app


app = build_app()
