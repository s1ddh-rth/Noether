"""Settings for Postgres / TimescaleDB connectivity."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = Field(default="timescaledb", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    database: str = Field(default="noether", alias="POSTGRES_DB")
    user: str = Field(default="noether", alias="POSTGRES_USER")
    password: str = Field(default="noether", alias="POSTGRES_PASSWORD")
    retention_days: int = Field(default=90, ge=1, alias="RETENTION_DAYS")


def dsn(s: StorageSettings | None = None) -> str:
    s = s or StorageSettings()
    return f"postgresql://{s.user}:{s.password}@{s.host}:{s.port}/{s.database}"


def async_dsn(s: StorageSettings | None = None) -> str:
    s = s or StorageSettings()
    return f"postgresql+asyncpg://{s.user}:{s.password}@{s.host}:{s.port}/{s.database}"
