## Context

LangGraph gives a state-machine view of multi-agent workflows that fits
operator question-answering well: a router classifies intent, then one
or more specialised agents fetch data, then a synthesiser composes the
final response and (when relevant) a Vega-Lite chart. Memory is
non-trivial — Graphiti is the OSS choice (SPEC section 5) and gives temporal
edges out of the box.

The "boring tech wins" rule (SPEC section 11) applies hardest here: it is easy
to over-engineer this surface. We deliberately keep the graph shallow.

## Goals / Non-Goals

**Goals:**
- One `/chat` endpoint that accepts a question and a session id.
- Router → 1-3 sub-agents in parallel where possible → synthesiser.
- Tools call the existing service APIs (`/forecast`, `/anomaly`,
  `/explain`) and library functions (`libs/rag.retrieve`,
  `libs/storage.range`).
- Memory: every turn writes facts to Graphiti; the router pulls
  relevant memories at session start.
- Default LLM: Ollama with `llama3.3:8b-instruct` or `qwen2.5:7b`.
  Cloud LLMs behind `LLM_BACKEND` env.
- Demo question must succeed end-to-end with citations and a chart
  (SPEC section 8 Milestone 3).

**Non-Goals (per SPEC section 9):**
- Fine-tuning domain LLMs.
- Custom embedding training (handled in `add-rag-pipeline`, not here).
- Real-time websocket streaming to the frontend (poll-based).
- Multi-tenant memory isolation (single-tenant assumption at v0.1).

## Decisions

- **Graph topology:**
    Router → {SQL, RAG, MultimodalRAG, Forecast, Anomaly} (parallel) → Viz?
        → Synthesiser → Memory writer
- **Tool contract:** every tool returns a typed Pydantic `ToolResult`
  with `summary: str`, `data: dict | None`, `citations: list[str]`,
  `vega_spec: dict | None`. The synthesiser sees only `ToolResult`s.
- **Provider abstraction:** thin wrapper exposing `chat(messages, tools,
  json_mode) -> Message`. Ollama implementation default; cloud
  implementations behind `LLM_BACKEND` env. No new abstraction layer
  beyond what LangChain already gives — we lean on its `ChatModel`
  classes.
- **Session model:** session id is opaque; per-session state lives in
  Postgres (a small `chat_sessions` table); Graphiti stores extracted
  facts independently.
- **Memory writes:** at end of each turn, the synthesiser emits
  `MemoryFact { subject, predicate, object, t_valid }` items; the
  Memory writer pushes them to Graphiti.
- **Citations:** each RAG/MultimodalRAG result carries `doc_id +
  chunk_idx`; the synthesiser must include them in the final answer.
- **Latency budget:** end-to-end p95 under 6 s on the laptop default
  Ollama model — acceptable given local inference.

## Risks / Trade-offs

- **Local LLM quality variance:** Llama-3.3-8B / Qwen-2.5-7B sometimes
  fail to call tools cleanly. Mitigation: prompt templates with strict
  JSON schemas; retry once with a stricter system message.
- **Graphiti complexity:** Graphiti adds a graph DB and an embedding
  model dependency. Mitigation: bound memory to the last N=200 facts
  per session; document the v0.2 path for richer memory.
- **Tool fan-out cost:** parallel tool calls multiply local-LLM latency.
  Mitigation: router emits a minimal toolset (1-3 tools) per turn.
- SPEC section 11 risk: scope creep. We resist adding plan-and-execute,
  reflexion, or chain-of-thought verifier loops at v0.1.
