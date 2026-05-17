"""Settings for the anomaly-detector service."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnomalySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    window_seconds: int = Field(default=60, ge=10, alias="ANOMALY_WINDOW_S")
    stride_seconds: int = Field(default=5, ge=1, alias="ANOMALY_STRIDE_S")

    # Tags scored by the ensemble. Default is a small, well-conditioned subset
    # of TEP variables; the full 52-tag panel can OOM small dev hosts when
    # PyOD's MCD covariance is fit on rolling 60-min training windows.
    tags: str = Field(
        default="XMEAS_1,XMEAS_2,XMEAS_3,XMEAS_4,XMEAS_5,XMEAS_6,XMEAS_7,XMEAS_8,XMV_1,XMV_2",
        alias="ANOMALY_TAGS",
    )

    # Baseline window (minutes of recent clean data) used to fit the ensemble
    # on startup. Smaller for fast smoke; bump for stable production fits.
    baseline_minutes: int = Field(default=30, ge=5, alias="ANOMALY_BASELINE_MIN")

    # Wait for at least this many minutes of ingested data before fitting.
    warmup_minutes: int = Field(default=5, ge=1, alias="ANOMALY_WARMUP_MIN")

    threshold: float = Field(default=0.95, ge=0.0, le=1.0, alias="ANOMALY_THRESHOLD")

    model_dir: Path = Field(default=Path("/app/models"), alias="MODEL_DIR")
    ensemble_path: Path = Field(
        default=Path("/app/models/anomaly_ensemble.joblib"),
        alias="ANOMALY_ENSEMBLE_PATH",
    )

    metrics_port: int = Field(default=9103, ge=1, le=65535, alias="METRICS_PORT")

    offline_mode: bool = Field(default=True, alias="OFFLINE_MODE")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]
