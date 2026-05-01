"""Settings for the agent service."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LlmBackend = Literal["ollama", "openai", "anthropic", "gemini"]


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = Field(default="0.0.0.0", alias="AGENT_HOST")
    port: int = Field(default=8100, alias="AGENT_PORT")
    api_key: str = Field(default="changeme-please", alias="AGENT_API_KEY")

    llm_backend: LlmBackend = Field(default="ollama", alias="LLM_BACKEND")

    offline_mode: bool = Field(default=True, alias="OFFLINE_MODE")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
