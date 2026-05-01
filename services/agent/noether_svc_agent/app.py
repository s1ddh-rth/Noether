"""FastAPI app construction for the agent service."""

from __future__ import annotations

from fastapi import FastAPI
from noether_ingest.logging import configure  # type: ignore[import-untyped]

from noether_svc_agent.config import AgentSettings
from noether_svc_agent.routers import health as health_router


def build_app() -> FastAPI:
    settings = AgentSettings()
    configure(settings.log_level, service="agent")

    app = FastAPI(
        title="Noether Agent",
        version="0.1.0",
        description="LangGraph-orchestrated /chat over plant data, RAG, and forecasts.",
    )
    app.state.settings = settings
    app.include_router(health_router.router)
    return app


app = build_app()
