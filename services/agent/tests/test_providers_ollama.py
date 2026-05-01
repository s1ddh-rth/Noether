"""OllamaProvider: HTTP wire format + response parsing.

Uses httpx.MockTransport — no real network, no Ollama install needed.
"""

from __future__ import annotations

import json

import httpx
import pytest
from noether_svc_agent.providers import ChatResponse, Message, OllamaProvider


def _ollama_response(content: str, model: str = "llama3.3:8b") -> dict[str, object]:
    """Shape Ollama's /api/chat actually returns (subset we care about)."""
    return {
        "model": model,
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
    }


def _make_provider(handler: httpx.MockTransport, *, model: str = "llama3.3:8b") -> OllamaProvider:
    client = httpx.AsyncClient(transport=handler, base_url="http://test")
    return OllamaProvider(host="http://test", model=model, client=client)


@pytest.mark.asyncio
async def test_posts_to_api_chat_with_messages() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_ollama_response("hi back"))

    provider = _make_provider(httpx.MockTransport(handler))
    out = await provider.chat([Message(role="user", content="hello")])

    assert captured["url"] == "http://test/api/chat"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "llama3.3:8b"
    assert body["stream"] is False
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    assert "format" not in body  # json_mode default off

    assert isinstance(out, ChatResponse)
    assert out.content == "hi back"
    assert out.finish_reason == "stop"
    assert out.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_json_mode_sets_format_field() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_ollama_response('{"intent": "rag"}'))

    provider = _make_provider(httpx.MockTransport(handler))
    await provider.chat([Message(role="user", content="classify")], json_mode=True)
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["format"] == "json"


@pytest.mark.asyncio
async def test_http_error_propagates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "model not loaded"})

    provider = _make_provider(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await provider.chat([Message(role="user", content="x")])


@pytest.mark.asyncio
async def test_passes_through_finish_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = _ollama_response("partial")
        body["done_reason"] = "length"
        return httpx.Response(200, json=body)

    provider = _make_provider(httpx.MockTransport(handler))
    out = await provider.chat([Message(role="user", content="x")])
    assert out.finish_reason == "length"


@pytest.mark.asyncio
async def test_aclose_is_safe_when_client_injected() -> None:
    """An injected client is owned by the test; aclose must not double-close it."""
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=_ollama_response("ok")))
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    provider = OllamaProvider(host="http://test", model="m", client=client)

    await provider.aclose()  # no-op: provider doesn't own this client
    # client is still usable
    await provider.chat([Message(role="user", content="x")])
    await client.aclose()
