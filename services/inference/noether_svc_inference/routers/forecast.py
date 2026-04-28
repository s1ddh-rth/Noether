"""POST /forecast — predict horizon-ahead value for one tag."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from noether_forecasting import (
    EnsembleForecaster,
    LightGBMForecaster,
    PatchTSTForecaster,
)
from pydantic import BaseModel, Field
from structlog import get_logger

from noether_svc_inference.deps import (
    LoadedForecaster,
    ModelRegistry,
    get_registry,
    require_api_key,
)

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
    model_kind: str
    latency_ms: int


def _dispatch(model: LoadedForecaster, series: pd.Series) -> object:
    """Each forecaster kind takes different inputs — handle them here."""
    if isinstance(model, LightGBMForecaster):
        from noether_forecasting.features import FeatureSpec, build_features

        X, _y = build_features(series, FeatureSpec(horizon_min=model.horizon_min))
        if X.empty:
            raise ValueError("history too short or too gappy after resampling")
        return model.predict(X)
    if isinstance(model, PatchTSTForecaster):
        return model.predict(series)
    if isinstance(model, EnsembleForecaster):
        from noether_forecasting.features import FeatureSpec, build_features

        X, _y = build_features(series, FeatureSpec(horizon_min=model.horizon_min))
        if X.empty:
            raise ValueError("history too short or too gappy after resampling")
        return model.predict(X, series)
    raise RuntimeError(f"unknown forecaster kind: {type(model).__name__}")


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

    try:
        result = _dispatch(model, series)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    latency_ms = int((time.monotonic() - started) * 1000)

    logger.info(
        "forecast.ok",
        request_id=request_id,
        tag=body.tag,
        model_kind=getattr(result, "model_kind", "unknown"),
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
        model_kind=result.model_kind,
        latency_ms=latency_ms,
    )
