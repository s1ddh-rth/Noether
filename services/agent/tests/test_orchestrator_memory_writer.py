"""MemoryWriterNode: fact extraction + persistence via MemoryStore Protocol."""

from __future__ import annotations

import pytest
from noether_memory import InMemoryStore
from noether_svc_agent.orchestrator import MemoryWriterNode
from noether_svc_agent.providers import MockProvider
from noether_svc_agent.tools import ToolResult


@pytest.mark.asyncio
async def test_extracts_and_writes_facts() -> None:
    provider = MockProvider(
        responses=['[{"subject": "FT-101", "predicate": "threshold_set", "object": "2.5"}]']
    )
    store = InMemoryStore()
    node = MemoryWriterNode(provider=provider, store=store)

    n = await node.write_turn(
        session_id="s1",
        question="Set FT-101 threshold to 2.5.",
        answer="OK, threshold updated to 2.5.",
        tool_results=[],
    )
    assert n == 1
    out = await store.retrieve("s1", query="FT-101", k=10)
    assert len(out) == 1
    assert out[0].subject == "FT-101"
    assert out[0].predicate == "threshold_set"
    assert out[0].object == "2.5"


@pytest.mark.asyncio
async def test_session_isolation_through_store() -> None:
    provider = MockProvider(
        responses=[
            '[{"subject": "valve", "predicate": "opened", "object": "V-1"}]',
            '[{"subject": "valve", "predicate": "opened", "object": "V-2"}]',
        ]
    )
    store = InMemoryStore()
    node = MemoryWriterNode(provider=provider, store=store)

    await node.write_turn("a", "q1", "a1", [])
    await node.write_turn("b", "q2", "a2", [])

    a_facts = await store.retrieve("a", query="valve", k=5)
    b_facts = await store.retrieve("b", query="valve", k=5)
    assert len(a_facts) == 1
    assert len(b_facts) == 1
    assert a_facts[0].object == "V-1"
    assert b_facts[0].object == "V-2"


@pytest.mark.asyncio
async def test_empty_array_means_zero_writes() -> None:
    provider = MockProvider(responses=["[]"])
    store = InMemoryStore()
    node = MemoryWriterNode(provider=provider, store=store)

    n = await node.write_turn("s1", "hi", "hello", [])
    assert n == 0
    assert await store.retrieve("s1", query="hi", k=5) == []


@pytest.mark.asyncio
async def test_malformed_json_yields_zero_not_exception() -> None:
    """Bad LLM output must never break a chat turn."""
    provider = MockProvider(responses=["this is prose, not JSON"])
    store = InMemoryStore()
    node = MemoryWriterNode(provider=provider, store=store)

    n = await node.write_turn("s1", "q", "a", [])
    assert n == 0


@pytest.mark.asyncio
async def test_drops_bad_rows_keeps_good_ones() -> None:
    provider = MockProvider(
        responses=[
            "["
            ' {"subject": "ok", "predicate": "is", "object": "fine"},'
            ' {"subject": "missing_pred"},'  # missing required keys
            ' "not even an object",'
            ' {"subject": "ok2", "predicate": "is", "object": "also fine"}'
            "]"
        ]
    )
    store = InMemoryStore()
    node = MemoryWriterNode(provider=provider, store=store)

    n = await node.write_turn("s1", "q", "a", [])
    assert n == 2
    assert {f.subject for f in await store.retrieve("s1", query="ok", k=10)} == {"ok", "ok2"}


@pytest.mark.asyncio
async def test_store_exception_returns_zero_not_raises() -> None:
    """Memory persistence is best-effort; never let it kill the chat turn."""

    class _BrokenStore:
        async def write_facts(self, *_a: object, **_k: object) -> None:
            raise RuntimeError("graphiti is down")

        async def retrieve(self, *_a: object, **_k: object) -> list[object]:
            return []

    provider = MockProvider(responses=['[{"subject": "x", "predicate": "y", "object": "z"}]'])
    node = MemoryWriterNode(provider=provider, store=_BrokenStore())  # type: ignore[arg-type]
    n = await node.write_turn("s1", "q", "a", [])
    assert n == 0


@pytest.mark.asyncio
async def test_strips_code_fences() -> None:
    provider = MockProvider(
        responses=['```json\n[{"subject": "x", "predicate": "y", "object": "z"}]\n```']
    )
    store = InMemoryStore()
    node = MemoryWriterNode(provider=provider, store=store)

    n = await node.write_turn("s1", "q", "a", [])
    assert n == 1


@pytest.mark.asyncio
async def test_tool_results_rendered_into_extraction_prompt() -> None:
    """The LLM should see the tool results when deciding what to persist."""
    provider = MockProvider(responses=["[]"])
    store = InMemoryStore()
    node = MemoryWriterNode(provider=provider, store=store)

    await node.write_turn(
        "s1",
        "Why did anomaly fire?",
        "Because FT-101 calibration drift.",
        [ToolResult(summary="anomaly score 0.83", citations=["alert-abc"])],
    )
    sent = provider.calls[0].messages[0].content
    assert "Why did anomaly fire?" in sent
    assert "Because FT-101 calibration drift." in sent
    assert "anomaly score 0.83" in sent
    assert "alert-abc" in sent
