"""InMemoryStore: write/retrieve roundtrip, eviction, session isolation."""

from __future__ import annotations

import pytest
from noether_memory import InMemoryStore, MemoryFact


def _fact(subject: str = "FT-101", predicate: str = "noted", object: str = "ok") -> MemoryFact:
    return MemoryFact(subject=subject, predicate=predicate, object=object)


@pytest.mark.asyncio
async def test_write_and_retrieve_roundtrip() -> None:
    store = InMemoryStore()
    await store.write_facts("s1", [_fact(subject="FT-101", predicate="anomaly", object="high")])
    out = await store.retrieve("s1", query="ft-101", k=5)
    assert len(out) == 1
    assert out[0].subject == "FT-101"


@pytest.mark.asyncio
async def test_retrieve_returns_most_recent_first() -> None:
    store = InMemoryStore()
    await store.write_facts(
        "s1", [_fact(object="first"), _fact(object="second"), _fact(object="third")]
    )
    out = await store.retrieve("s1", query="noted", k=10)
    assert [f.object for f in out] == ["third", "second", "first"]


@pytest.mark.asyncio
async def test_retrieve_caps_at_k() -> None:
    store = InMemoryStore()
    await store.write_facts("s1", [_fact(object=str(i)) for i in range(10)])
    out = await store.retrieve("s1", query="noted", k=3)
    assert len(out) == 3
    # Most recent (largest i) first.
    assert [f.object for f in out] == ["9", "8", "7"]


@pytest.mark.asyncio
async def test_session_isolation() -> None:
    store = InMemoryStore()
    await store.write_facts("s1", [_fact(subject="alpha")])
    await store.write_facts("s2", [_fact(subject="beta")])
    assert {f.subject for f in await store.retrieve("s1", query="alpha", k=10)} == {"alpha"}
    assert await store.retrieve("s2", query="alpha", k=10) == []


@pytest.mark.asyncio
async def test_eviction_at_session_cap() -> None:
    store = InMemoryStore(cap_per_session=3)
    await store.write_facts("s1", [_fact(object=str(i)) for i in range(5)])
    out = await store.retrieve("s1", query="noted", k=10)
    # Only the last 3 survive (objects "2", "3", "4"); newest first.
    assert [f.object for f in out] == ["4", "3", "2"]


@pytest.mark.asyncio
async def test_retrieve_from_unknown_session_is_empty() -> None:
    store = InMemoryStore()
    assert await store.retrieve("never-written", query="anything", k=5) == []


@pytest.mark.asyncio
async def test_substring_match_across_fields() -> None:
    store = InMemoryStore()
    await store.write_facts(
        "s1",
        [
            _fact(subject="XMEAS_3", predicate="threshold", object="adjusted"),
            _fact(subject="FT-101", predicate="alarm", object="suppressed"),
        ],
    )
    # Match on object field only.
    out = await store.retrieve("s1", query="suppressed", k=5)
    assert len(out) == 1
    assert out[0].subject == "FT-101"
