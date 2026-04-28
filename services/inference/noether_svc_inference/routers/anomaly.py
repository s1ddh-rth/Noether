"""POST /anomaly and POST /explain.

Both endpoints share a fitted `AnomalyEnsemble` produced by the
anomaly-detector service. The ensemble is loaded lazily and cached.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from noether_anomaly import AnomalyEnsemble, AnomalyResult, Explainer, TagContribution
from noether_storage import StorageSettings, async_dsn, pivot
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from structlog import get_logger

from noether_svc_inference.config import InferenceSettings
from noether_svc_inference.deps import get_settings, require_api_key

logger = get_logger().bind(component="anomaly-router")

router = APIRouter(tags=["anomaly"])


# ----------------------- request / response models -------------------------


class AnomalyRequest(BaseModel):
    tags: Annotated[list[str], Field(min_length=1, max_length=64)]
    start: datetime
    end: datetime


class AnomalyResponse(BaseModel):
    request_id: str
    score: float
    detectors: dict[str, float]
    tags: list[str]
    alert: bool
    latency_ms: int


class ExplainRequest(BaseModel):
    alert_id: UUID


class ExplainResponse(BaseModel):
    alert_id: UUID
    score: float
    contributions: list[TagContribution]
    latency_ms: int


# -------------------------- shared deps ------------------------------------


_ENSEMBLE_CACHE: AnomalyEnsemble | None = None


def _load_ensemble(settings: InferenceSettings) -> AnomalyEnsemble:
    global _ENSEMBLE_CACHE
    if _ENSEMBLE_CACHE is None:
        path = settings.model_dir / "anomaly_ensemble.joblib"
        if not path.exists():
            raise FileNotFoundError(
                f"anomaly ensemble not found at {path} — has the anomaly-detector "
                "service run long enough to fit a baseline?"
            )
        _ENSEMBLE_CACHE = AnomalyEnsemble.load(path)
    return _ENSEMBLE_CACHE


def _engine() -> object:
    # Build per-call to avoid sharing across uvicorn workers; cheap enough
    # for v0.1. Move to a module-level engine + lifespan hook later.
    return create_async_engine(async_dsn(StorageSettings()))


# ---------------------------- /anomaly -------------------------------------


@router.post("/anomaly", response_model=AnomalyResponse, dependencies=[Depends(require_api_key)])
async def anomaly(
    body: AnomalyRequest,
    settings: InferenceSettings = Depends(get_settings),
) -> AnomalyResponse:
    started = time.monotonic()
    request_id = str(uuid.uuid4())

    try:
        ensemble = _load_ensemble(settings)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    engine = _engine()
    try:
        df = await pivot(engine, body.tags, body.start, body.end)
    finally:
        await engine.dispose()

    if df.empty or len(df.dropna()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="window has too few samples after pivot/dropna",
        )
    df = df[body.tags].dropna()
    result: AnomalyResult = ensemble.score(df)

    latency_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "anomaly.scored",
        request_id=request_id,
        score=round(result.score, 4),
        alert=result.alert,
        latency_ms=latency_ms,
        status=200,
    )
    return AnomalyResponse(
        request_id=request_id,
        score=result.score,
        detectors=result.detectors.model_dump(),
        tags=result.tags,
        alert=result.alert,
        latency_ms=latency_ms,
    )


# ---------------------------- /explain -------------------------------------


@router.post("/explain", response_model=ExplainResponse, dependencies=[Depends(require_api_key)])
async def explain(
    body: ExplainRequest,
    settings: InferenceSettings = Depends(get_settings),
) -> ExplainResponse:
    started = time.monotonic()

    try:
        ensemble = _load_ensemble(settings)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    engine = _engine()
    try:
        async with engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT window_start, window_end, score, tags
                        FROM tag_anomalies
                        WHERE alert_id = :alert_id
                        """
                        ),
                        {"alert_id": str(body.alert_id)},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"alert_id {body.alert_id} not found",
            )
        df = await pivot(engine, list(row["tags"]), row["window_start"], row["window_end"])
    finally:
        await engine.dispose()

    df = df[list(row["tags"])].dropna()
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="alert window has no samples in tag_samples — retention may have purged",
        )

    explainer = Explainer(ensemble=ensemble)
    contributions = explainer.explain(df, alert_score=float(row["score"]))

    latency_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "anomaly.explained",
        alert_id=str(body.alert_id),
        n_contribs=len(contributions),
        latency_ms=latency_ms,
        status=200,
    )
    return ExplainResponse(
        alert_id=body.alert_id,
        score=float(row["score"]),
        contributions=contributions,
        latency_ms=latency_ms,
    )
