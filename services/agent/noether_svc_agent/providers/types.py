"""Provider protocol + the wire types used across all backends."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """One turn of the chat conversation as the LLM sees it."""

    role: Role
    content: str


class ChatResponse(BaseModel):
    """Provider-agnostic shape for a single completion."""

    content: str
    model: str = Field(min_length=1)
    finish_reason: str = Field(default="stop")
    latency_ms: float = Field(ge=0.0)


class ProviderCall(BaseModel):
    """Recorded call — only the MockProvider populates this, for test assertions."""

    messages: list[Message]
    json_mode: bool


@runtime_checkable
class Provider(Protocol):
    """Anything that can do a chat completion."""

    async def chat(self, messages: list[Message], *, json_mode: bool = False) -> ChatResponse: ...
