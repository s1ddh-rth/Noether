# libs/memory

Cross-session memory for the agent system. Stores typed facts extracted
from chat turns and retrieves the relevant ones for the next turn.

## Public API (this scaffold)

- `MemoryFact` — Pydantic model `{subject, predicate, object, t_valid}`.
- `MemoryStore` — Protocol with `write_facts(session_id, facts)` and
  `retrieve(session_id, query, k)`.
- `InMemoryStore` — list-backed reference impl used by unit tests and
  by the agent service when `MEMORY_BACKEND=memory`.

The Graphiti-backed adapter (`GraphitiStore`) lands in a later commit
and slots in behind the same Protocol.

## Test

```
uv run pytest libs/memory
```
