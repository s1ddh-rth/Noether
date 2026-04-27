"""POST /forecast — predict horizon-ahead value for one tag."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from structlog import get_logger

from noether_svc_inference.deps import ModelRegistry, get_registry, require_api_key

logger = get_logger().bind(component="forecast-router")

router = APIRouter(prefix="/forecast", tags=["forecast"])


class ForecastSamplePoint(BaseModel):
    ts: datetime
    value: float


class ForecastRequest(BaseModel):
    tag: Annotated[str, Field(min_length=1, max_length=64)]
    history: Annotated[
        list[ForecastSamplePoint],
        Field(min_length=120, description="Trailing 1-Hz or 1-min samples; need >=120 points"),
    ]


class ForecastResponse(BaseModel):
    request_id: str
    tag: str
    horizon_min: int
    point: float
    lower: float
    upper: float
    model_version: str
    latency_ms: int


@router.post("", response_model=ForecastResponse, dependencies=[Depends(require_api_key)])
def forecast(
    body: ForecastRequest,
    registry: ModelRegistry = Depends(get_registry),
) -> ForecastResponse:
    started = time.monotonic()
    request_id = str(uuid.uuid4())

    try:
        model = registry.get(body.tag)
    except FileNotFoundError as exc:
        logger.warning("forecast.unknown_tag", request_id=request_id, tag=body.tag)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    series = pd.Series(
        [p.value for p in body.history],
        index=pd.DatetimeIndex([p.ts for p in body.history], tz="UTC"),
    ).sort_index()

    from noether_forecasting.features import FeatureSpec, build_features

    spec = FeatureSpec(horizon_min=model.horizon_min)
    X, _y = build_features(series, spec)
    if X.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="history too short or too gappy after resampling — provide more samples",
        )

    result = model.predict(X)
    latency_ms = int((time.monotonic() - started) * 1000)

    logger.info(
        "forecast.ok",
        request_id=request_id,
        tag=body.tag,
        horizon_min=result.horizon_min,
        latency_ms=latency_ms,
        status=200,
    )

    return ForecastResponse(
        request_id=request_id,
        tag=result.tag,
        horizon_min=result.horizon_min,
        point=result.point,
        lower=result.lower,
        upper=result.upper,
        model_version=result.model_version,
        latency_ms=latency_ms,
    )
