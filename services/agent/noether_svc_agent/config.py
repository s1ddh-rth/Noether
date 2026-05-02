"""Settings for the agent service."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LlmBackend = Literal["ollama", "openai", "anthropic", "gemini"]


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Service binding ──────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", alias="AGENT_HOST")
    port: int = Field(default=8100, alias="AGENT_PORT")
    api_key: str = Field(default="changeme-please", alias="AGENT_API_KEY")

    # ── LLM provider ─────────────────────────────────────────────────────────
    llm_backend: LlmBackend = Field(default="ollama", alias="LLM_BACKEND")
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")

    # ── Upstream services (consumed by the tool / memory factory) ──────────
    inference_url: str = Field(default="http://localhost:8000", alias="INFERENCE_URL")
    inference_api_key: str = Field(default="changeme-please", alias="INFERENCE_API_KEY")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="changeme-please", alias="NEO4J_PASSWORD")

    # ── Postgres (for the SQL tool's AsyncEngine) ───────────────────────────
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="noether", alias="POSTGRES_DB")
    postgres_user: str = Field(default="noether", alias="POSTGRES_USER")
    postgres_password: str = Field(default="noether", alias="POSTGRES_PASSWORD")

    # ── Operational ──────────────────────────────────────────────────────────
    offline_mode: bool = Field(default=True, alias="OFFLINE_MODE")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
