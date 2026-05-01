"""MockProvider: deterministic LLM stub for tests."""

from __future__ import annotations

import pytest
from noether_svc_agent.providers import (
    ChatResponse,
    Message,
    MockProvider,
    Provider,
)


def test_satisfies_provider_protocol() -> None:
    p = MockProvider(responses=["hi"])
    # Runtime-checkable Protocol — explicit isinstance proves the contract.
    assert isinstance(p, Provider)


@pytest.mark.asyncio
async def test_returns_canned_responses_in_order() -> None:
    p = MockProvider(responses=["one", "two"])
    msgs = [Message(role="user", content="anything")]

    r1 = await p.chat(msgs)
    r2 = await p.chat(msgs)

    assert isinstance(r1, ChatResponse)
    assert r1.content == "one"
    assert r2.content == "two"


@pytest.mark.asyncio
async def test_response_carries_model_name_and_latency() -> None:
    p = MockProvider(responses=["ok"], model="mock-7b")
    out = await p.chat([Message(role="user", content="ping")])
    assert out.model == "mock-7b"
    assert out.latency_ms >= 0.0
    assert out.finish_reason == "stop"


@pytest.mark.asyncio
async def test_exhausted_response_queue_raises() -> None:
    p = MockProvider(responses=["only"])
    await p.chat([Message(role="user", content="x")])
    with pytest.raises(RuntimeError, match="exhausted"):
        await p.chat([Message(role="user", content="x")])


@pytest.mark.asyncio
async def test_records_received_messages_for_assertions() -> None:
    """Tests assert what got sent to the LLM via .calls."""
    p = MockProvider(responses=["ok"])
    sent = [Message(role="system", content="be brief"), Message(role="user", content="hi")]
    await p.chat(sent, json_mode=True)
    assert len(p.calls) == 1
    assert p.calls[0].messages == sent
    assert p.calls[0].json_mode is True


def test_message_role_is_constrained() -> None:
    """Role is a Literal — invalid values rejected at validation time."""
    from pydantic import ValidationError

    Message(role="user", content="ok")
    with pytest.raises(ValidationError):
        Message(role="not-a-role", content="x")  # type: ignore[arg-type]
