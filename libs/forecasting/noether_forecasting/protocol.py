"""Forecaster Protocol — common surface for LGBM / PatchTST / ensemble.

We keep the protocol intentionally lenient: it covers the metadata and
persistence surface that the inference service and eval harness need to
treat artefacts uniformly. The fit/predict signatures vary per model
(LGBM takes feature DataFrames, PatchTST takes raw series), so they live
on the concrete classes — calling code dispatches via `model_kind`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

ModelKind = Literal["lgbm", "patchtst", "ensemble"]


class ForecastResult(BaseModel):
    """Common forecast envelope returned by every forecaster's predict path."""

    tag: str
    horizon_min: int
    point: float
    lower: float
    upper: float
    model_version: str
    model_kind: ModelKind


@runtime_checkable
class Forecaster(Protocol):
    """Common metadata + persistence surface for every forecaster kind."""

    tag: str
    horizon_min: int
    model_version: str
    model_kind: ModelKind

    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path) -> Forecaster: ...
