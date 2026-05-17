"""Settings for the Kafka -> Timescale consumer."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConsumerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    kafka_bootstrap: str = Field(default="redpanda:9092", alias="KAFKA_BOOTSTRAP")
    kafka_topic_plant_tags: str = Field(default="plant.tags", alias="KAFKA_TOPIC_PLANT_TAGS")
    kafka_group_id: str = Field(default="noether-storage-consumer", alias="KAFKA_GROUP_ID")

    batch_size: int = Field(default=500, ge=1, le=10000, alias="BATCH_SIZE")
    batch_max_wait_ms: int = Field(default=1000, ge=10, alias="BATCH_MAX_WAIT_MS")

    metrics_port: int = Field(default=9102, ge=1, le=65535, alias="METRICS_PORT")

    offline_mode: bool = Field(default=True, alias="OFFLINE_MODE")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
