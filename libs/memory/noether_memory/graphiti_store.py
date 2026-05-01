"""Graphiti-backed `MemoryStore` for cross-session memory on Neo4j.

Graphiti's API is "give me unstructured text, I'll extract entities
and temporal edges via an LLM" (see graphiti-core's `add_episode`).
Our `MemoryFact`s are already structured (subject, predicate, object,
t_valid). We bridge the two by serialising each fact as a tagged
text episode — Graphiti then runs its own extraction over that
structured text, which gives us its temporal edges + entity dedup
"for free" without us reimplementing them.

Per-session scoping: the episode body is prefixed with `[session=...]`
and the same tag is added to retrieval queries, so search results
focus on the active session. Cross-session retrieval (the v0.2 path)
just drops the prefix.

Cost: every `write_facts` call triggers Graphiti's internal LLM
extraction (~1-3 s per fact on a local model). The chat endpoint
(task 7) calls this as a fire-and-forget background task after the
synthesised answer has been streamed to the operator, so the user
never waits for memory writes.

Lazy import of `graphiti_core`: the module loads even without the
`[graphiti]` extra installed, but instantiating `GraphitiStore`
fails fast with a clear install hint. Keeps `from noether_memory
import GraphitiStore` cheap in tests that just need the type.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from noether_memory.models import MemoryFact

if TYPE_CHECKING:
    from graphiti_core import Graphiti

logger = logging.getLogger(__name__)

_SESSION_TAG_PREFIX = "[session="


def _tag(session_id: str) -> str:
    return f"{_SESSION_TAG_PREFIX}{session_id}]"


class GraphitiStore:
    """`MemoryStore` impl backed by graphiti-core + Neo4j.

    Args:
        client:    pre-built `Graphiti` instance, used in production
                   so the same client (with its connection pool) is
                   shared across the service. Tests pass a `Mock`.

    Use `GraphitiStore.connect(uri, user, password)` to construct one
    against a live Neo4j; that path imports `graphiti_core` lazily.
    """

    def __init__(self, client: Graphiti) -> None:
        self._client = client

    @classmethod
    def connect(cls, uri: str, user: str, password: str) -> GraphitiStore:
        """Build a `GraphitiStore` against a live Neo4j instance."""
        try:
            from graphiti_core import Graphiti
        except ImportError as e:  # pragma: no cover — exercised only when the extra is missing
            raise ImportError(
                "GraphitiStore requires the [graphiti] extra. "
                "Install with: uv pip install 'noether-memory[graphiti]'"
            ) from e
        return cls(client=Graphiti(uri, user, password))

    async def write_facts(self, session_id: str, facts: list[MemoryFact]) -> None:
        for fact in facts:
            body = f"{_tag(session_id)} ({fact.subject}) ({fact.predicate}) ({fact.object})"
            try:
                await self._client.add_episode(
                    name=f"{session_id}:{fact.t_valid.isoformat()}",
                    episode_body=body,
                    source_description=f"chat session {session_id}",
                    reference_time=fact.t_valid,
                )
            except Exception:
                logger.warning(
                    "graphiti.write_failed",
                    exc_info=True,
                    extra={"session_id": session_id, "fact": fact.model_dump(mode="json")},
                )

    async def retrieve(self, session_id: str, query: str, k: int) -> list[MemoryFact]:
        # Tag the query so Graphiti's vector search focuses on this session.
        tagged = f"{_tag(session_id)} {query}"
        try:
            results = await self._client.search(query=tagged, num_results=k)
        except Exception:
            logger.warning("graphiti.search_failed", exc_info=True)
            return []
        return [_to_fact(r) for r in results if _to_fact(r) is not None]  # type: ignore[misc]


def _to_fact(edge: Any) -> MemoryFact | None:
    """Best-effort map of a Graphiti EntityEdge back to a `MemoryFact`.

    Graphiti's edges carry source/target node info plus the edge name
    (relationship type). We treat:
        source_node_name    → subject
        edge_name           → predicate
        target_node_name    → object
        valid_at            → t_valid

    If the edge is missing any required piece, drop it rather than
    surfacing a partial fact — bad data is worse than no data here.
    """
    try:
        subject = getattr(edge, "source_node_name", None)
        predicate = getattr(edge, "name", None)
        obj = getattr(edge, "target_node_name", None)
        t_valid = getattr(edge, "valid_at", None) or getattr(edge, "created_at", None)
        if not (subject and predicate and obj):
            return None
        if t_valid is None:
            t_valid = datetime.now(UTC)
        return MemoryFact(subject=subject, predicate=predicate, object=obj, t_valid=t_valid)
    except (AttributeError, ValueError):
        return None
