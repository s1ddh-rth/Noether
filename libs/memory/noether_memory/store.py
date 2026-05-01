"""MemoryStore protocol + an in-memory reference implementation.

The Protocol is the contract every backend (Graphiti, in-memory, future
SQLite) must satisfy. The `InMemoryStore` is what unit tests and dev
mode use — it keeps the latest N facts per session in a deque-style
list and does naive substring matching for retrieval.

Why so simple here: the real semantic-search retrieval lives in the
Graphiti adapter (added with task 6 in the change proposal). Tests for
the orchestrator's memory plumbing only need a deterministic store
that round-trips facts in insertion order — that's all this is.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Protocol, runtime_checkable

from noether_memory.models import MemoryFact

DEFAULT_PER_SESSION_CAP = 200


@runtime_checkable
class MemoryStore(Protocol):
    """Anything that can persist and retrieve `MemoryFact`s by session."""

    def write_facts(self, session_id: str, facts: list[MemoryFact]) -> None: ...

    def retrieve(self, session_id: str, query: str, k: int) -> list[MemoryFact]: ...


class InMemoryStore:
    """Bounded per-session deque of `MemoryFact`s with substring retrieval.

    Args:
        cap_per_session: oldest facts evict once a session crosses this
            cap. Mirrors the design constraint (last 200 facts per
            session) so unit tests can exercise the same eviction
            behaviour the Graphiti adapter will need.
    """

    def __init__(self, cap_per_session: int = DEFAULT_PER_SESSION_CAP) -> None:
        self._cap = cap_per_session
        self._by_session: dict[str, deque[MemoryFact]] = defaultdict(
            lambda: deque(maxlen=self._cap)
        )

    def write_facts(self, session_id: str, facts: list[MemoryFact]) -> None:
        bucket = self._by_session[session_id]
        for fact in facts:
            bucket.append(fact)

    def retrieve(self, session_id: str, query: str, k: int) -> list[MemoryFact]:
        bucket = self._by_session.get(session_id)
        if not bucket:
            return []
        needle = query.lower()
        scored = [
            f
            for f in bucket
            if needle in f.subject.lower()
            or needle in f.predicate.lower()
            or needle in f.object.lower()
        ]
        # Most recent first — chat memory wants recency over fuzzy match.
        scored.reverse()
        return scored[:k]
