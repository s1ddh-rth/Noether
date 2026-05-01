"""Deterministic LLM stub. Used by every unit test that touches a provider."""

from __future__ import annotations

import time

from noether_svc_agent.providers.types import ChatResponse, Message, ProviderCall


class MockProvider:
    """Returns canned responses in order; records each call.

    Args:
        responses: list of strings to dispense from on successive `chat`
            calls. Once exhausted, further calls raise `RuntimeError`.
        model: name reported back in `ChatResponse.model`.

    Tests assert on `MockProvider.calls` to verify the orchestrator
    sent the expected `messages` / `json_mode` to the LLM.
    """

    def __init__(self, responses: list[str], *, model: str = "mock-7b") -> None:
        self._responses = list(responses)
        self._model = model
        self.calls: list[ProviderCall] = []

    async def chat(
        self,
        messages: list[Message],
        *,
        json_mode: bool = False,
    ) -> ChatResponse:
        if not self._responses:
            raise RuntimeError("MockProvider response queue exhausted")
        start = time.perf_counter()
        next_response = self._responses.pop(0)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.calls.append(ProviderCall(messages=messages, json_mode=json_mode))
        return ChatResponse(
            content=next_response,
            model=self._model,
            finish_reason="stop",
            latency_ms=elapsed_ms,
        )
