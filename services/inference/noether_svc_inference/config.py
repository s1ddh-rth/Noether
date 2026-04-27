"""Settings for the inference service."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InferenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = Field(default="0.0.0.0", alias="INFERENCE_HOST")
    port: int = Field(default=8000, alias="INFERENCE_PORT")
    model_dir: Path = Field(default=Path("/app/models"), alias="MODEL_DIR")
    api_key: str = Field(default="changeme-please", alias="INFERENCE_API_KEY")

    forecast_horizon_min: int = Field(default=30, alias="FORECAST_HORIZON_MIN")

    offline_mode: bool = Field(default=True, alias="OFFLINE_MODE")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
