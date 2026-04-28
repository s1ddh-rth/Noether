"""FastAPI app construction."""

from __future__ import annotations

from fastapi import FastAPI
from noether_ingest.logging import configure

from noether_svc_inference.config import InferenceSettings
from noether_svc_inference.routers import anomaly as anomaly_router
from noether_svc_inference.routers import forecast as forecast_router
from noether_svc_inference.routers import health as health_router


def build_app() -> FastAPI:
    settings = InferenceSettings()
    configure(settings.log_level, service="inference")

    app = FastAPI(
        title="Noether Inference",
        version="0.1.0",
        description="Forecast / anomaly / explain endpoints.",
    )
    app.include_router(health_router.router)
    app.include_router(forecast_router.router)
    app.include_router(anomaly_router.router)
    return app


app = build_app()
