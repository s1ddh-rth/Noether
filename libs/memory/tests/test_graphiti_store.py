"""GraphitiStore: write/retrieve translation around a mocked graphiti-core client.

We don't need a live Neo4j to verify our adapter — only the wire shape
(what gets passed to `add_episode` and `search`) and how
`EntityEdge`-shaped objects map back to `MemoryFact`. Integration
tests against a real Neo4j live with the compose-smoke harness.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from noether_memory import GraphitiStore, MemoryFact


def _store() -> tuple[GraphitiStore, AsyncMock, AsyncMock]:
    """Return a GraphitiStore wired to mocked add_episode + search."""
    add_episode = AsyncMock()
    search = AsyncMock(return_value=[])
    client = SimpleNamespace(add_episode=add_episode, search=search)
    return GraphitiStore(client=client), add_episode, search  # type: ignore[arg-type]


def _edge(
    *,
    subject: str = "FT-101",
    predicate: str = "threshold_set",
    obj: str = "2.5",
    valid_at: datetime | None = None,
) -> SimpleNamespace:
    """Mimic graphiti's EntityEdge shape — only the attrs we read."""
    return SimpleNamespace(
        source_node_name=subject,
        name=predicate,
        target_node_name=obj,
        valid_at=valid_at,
        created_at=valid_at,
    )


@pytest.mark.asyncio
async def test_write_facts_serialises_each_fact_as_an_episode() -> None:
    store, add_episode, _search = _store()
    ts = datetime(2026, 4, 30, 14, 23, tzinfo=UTC)

    await store.write_facts(
        "sess-A",
        [
            MemoryFact(subject="FT-101", predicate="threshold_set", object="2.5", t_valid=ts),
            MemoryFact(subject="V-203", predicate="state", object="open", t_valid=ts),
        ],
    )

    assert add_episode.await_count == 2
    args = add_episode.call_args_list

    body0 = args[0].kwargs["episode_body"]
    assert "[session=sess-A]" in body0
    assert "(FT-101)" in body0
    assert "(threshold_set)" in body0
    assert "(2.5)" in body0
    assert args[0].kwargs["reference_time"] == ts
    assert "sess-A" in args[0].kwargs["name"]

    body1 = args[1].kwargs["episode_body"]
    assert "[session=sess-A]" in body1
    assert "(V-203)" in body1


@pytest.mark.asyncio
async def test_retrieve_passes_session_tagged_query() -> None:
    store, _add, search = _store()
    ts = datetime(2026, 4, 30, 14, 23, tzinfo=UTC)
    search.return_value = [_edge(valid_at=ts)]

    out = await store.retrieve("sess-A", "FT-101 calibration", k=7)

    assert search.await_count == 1
    sent_query = search.call_args.kwargs["query"]
    assert sent_query.startswith("[session=sess-A]")
    assert "FT-101 calibration" in sent_query
    assert search.call_args.kwargs["num_results"] == 7

    assert len(out) == 1
    assert out[0].subject == "FT-101"
    assert out[0].predicate == "threshold_set"
    assert out[0].object == "2.5"
    assert out[0].t_valid == ts


@pytest.mark.asyncio
async def test_retrieve_drops_partial_edges() -> None:
    """Edges missing required fields are dropped, not surfaced as half-facts."""
    store, _add, search = _store()
    ts = datetime(2026, 4, 30, 14, 23, tzinfo=UTC)
    search.return_value = [
        _edge(subject="ok", predicate="is", obj="fine", valid_at=ts),
        SimpleNamespace(source_node_name=None, name="x", target_node_name="y", valid_at=ts),
        _edge(subject="ok2", predicate="is", obj="also fine", valid_at=ts),
    ]
    out = await store.retrieve("s", "anything", k=10)
    assert {f.subject for f in out} == {"ok", "ok2"}


@pytest.mark.asyncio
async def test_write_failure_swallowed_per_fact() -> None:
    """One bad add_episode shouldn't sink the rest of the batch."""
    store, add_episode, _search = _store()
    add_episode.side_effect = [None, RuntimeError("neo4j unavailable"), None]

    await store.write_facts(
        "s",
        [
            MemoryFact(subject="a", predicate="p", object="o"),
            MemoryFact(subject="b", predicate="p", object="o"),
            MemoryFact(subject="c", predicate="p", object="o"),
        ],
    )
    # All three were attempted; the middle one's failure was logged but didn't propagate.
    assert add_episode.await_count == 3


@pytest.mark.asyncio
async def test_search_failure_returns_empty_not_raises() -> None:
    """Memory retrieval is best-effort — degraded mode is fine, crashed turn is not."""
    store, _add, search = _store()
    search.side_effect = RuntimeError("neo4j down")

    out = await store.retrieve("s", "x", k=5)
    assert out == []


@pytest.mark.asyncio
async def test_edge_without_valid_at_falls_back_to_now() -> None:
    """Some Graphiti edges (especially older ones) lack temporal bounds."""
    store, _add, search = _store()
    search.return_value = [
        SimpleNamespace(
            source_node_name="x",
            name="y",
            target_node_name="z",
            valid_at=None,
            created_at=None,
        )
    ]
    before = datetime.now(UTC)
    out = await store.retrieve("s", "x", k=5)
    after = datetime.now(UTC)

    assert len(out) == 1
    assert before <= out[0].t_valid <= after
