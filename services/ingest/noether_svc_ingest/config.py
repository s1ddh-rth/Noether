"""Settings for the ingest service. All values overridable via environment."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    kafka_bootstrap: str = Field(default="redpanda:9092", alias="KAFKA_BOOTSTRAP")
    kafka_topic_plant_tags: str = Field(default="plant.tags", alias="KAFKA_TOPIC_PLANT_TAGS")

    replay_hz: float = Field(default=1.0, gt=0.0, le=1000.0, alias="REPLAY_HZ")
    sim_seed: int = Field(default=42, alias="SIM_SEED")
    fault_profile: str = Field(default="none", alias="FAULT_PROFILE")
    fault_start_s: int = Field(default=0, ge=0, alias="FAULT_START_S")

    metrics_port: int = Field(default=9101, ge=1, le=65535, alias="METRICS_PORT")

    offline_mode: bool = Field(default=True, alias="OFFLINE_MODE")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
