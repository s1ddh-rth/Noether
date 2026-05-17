"""Cross-session memory for the agent system.

Public API (scaffold):
    MemoryFact     — typed (subject, predicate, object, t_valid) row
    MemoryStore    — Protocol; backends plug in here
    InMemoryStore  — list-backed reference impl for tests + dev

The Graphiti-backed adapter lands in a later commit behind the same
Protocol. Keeping this scaffold small and dependency-light means the
agent service can import `MemoryStore` without dragging Neo4j into unit
tests.
"""

from noether_memory.graphiti_store import GraphitiStore
from noether_memory.models import MemoryFact
from noether_memory.store import InMemoryStore, MemoryStore

__all__ = [
    "GraphitiStore",
    "InMemoryStore",
    "MemoryFact",
    "MemoryStore",
]
