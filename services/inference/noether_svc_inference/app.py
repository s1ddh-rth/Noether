"""FastAPI app construction."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from noether_anomaly import AnomalyEnsemble
from noether_ingest.logging import configure
from noether_storage import StorageSettings, async_dsn
from sqlalchemy.ext.asyncio import create_async_engine

from noether_svc_inference.config import InferenceSettings
from noether_svc_inference.routers import anomaly as anomaly_router
from noether_svc_inference.routers import forecast as forecast_router
from noether_svc_inference.routers import health as health_router


class EnsembleHolder:
    """Lazy, lock-guarded slot for the fitted AnomalyEnsemble.

    Loaded from disk on first /anomaly or /explain request — the
    anomaly-detector service may not have written the artifact yet at
    inference startup, so eager-loading would fail boot.
    """

    def __init__(self, model_dir: Path) -> None:
        self._dir = model_dir
        self._cache: AnomalyEnsemble | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> AnomalyEnsemble:
        if self._cache is not None:
            return self._cache
        async with self._lock:
            if self._cache is None:
                path = self._dir / "anomaly_ensemble.joblib"
                if not path.exists():
                    raise FileNotFoundError(
                        f"anomaly ensemble not found at {path} — has the "
                        "anomaly-detector service run long enough to fit a baseline?"
                    )
                self._cache = AnomalyEnsemble.load(path)
        return self._cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: InferenceSettings = app.state.settings
    engine = create_async_engine(async_dsn(StorageSettings()))
    app.state.engine = engine
    app.state.ensemble_holder = EnsembleHolder(settings.model_dir)
    try:
        yield
    finally:
        await engine.dispose()


def build_app() -> FastAPI:
    settings = InferenceSettings()
    configure(settings.log_level, service="inference")

    app = FastAPI(
        title="Noether Inference",
        version="0.1.0",
        description="Forecast / anomaly / explain endpoints.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(health_router.router)
    app.include_router(forecast_router.router)
    app.include_router(anomaly_router.router)
    return app


app = build_app()
