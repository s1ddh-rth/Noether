"""Ollama HTTP adapter.

Ollama exposes `/api/chat` accepting `{model, messages, stream, format}`
and returning `{message: {content, role}, done_reason, ...}`. We hit it
non-streaming for now — streaming lands with the SSE `/chat` mode in
task 7.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from noether_svc_agent.providers.types import ChatResponse, Message

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.3:8b-instruct-q4_K_M"
DEFAULT_TIMEOUT_S = 120.0


class OllamaProvider:
    """Talk to a local (or in-cluster) Ollama instance over HTTP.

    Args:
        host: base URL — `http://localhost:11434` for `docker compose`,
            `http://ollama:11434` inside the compose network.
        model: tag pulled from the Ollama registry (must be pulled in
            advance — air-gap rule).
        timeout_s: per-request timeout. Local LLMs on CPU can take a
            while; 120 s default matches the design's p95 < 6 s budget
            with headroom for cold starts.
        client: inject a pre-built `httpx.AsyncClient` for tests; if
            None, one is created on first call and reused.
    """

    def __init__(
        self,
        host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout_s)
        return self._client

    async def chat(
        self,
        messages: list[Message],
        *,
        json_mode: bool = False,
    ) -> ChatResponse:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [m.model_dump() for m in messages],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        start = time.perf_counter()
        resp = await client.post(f"{self._host}/api/chat", json=payload)
        resp.raise_for_status()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        body = resp.json()

        return ChatResponse(
            content=body["message"]["content"],
            model=body.get("model", self._model),
            finish_reason=body.get("done_reason", "stop"),
            latency_ms=elapsed_ms,
        )

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None
