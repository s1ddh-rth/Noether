## 1. Scaffolding

- [x] 1.1 Create `services/agent/` with FastAPI app, `pyproject.toml`,
      `README.md`. (Dockerfile lands with task 2.x when the agent
      profile gets added to `docker-compose.yml`.)
- [x] 1.2 Create `libs/memory/` package with `MemoryFact` model,
      `MemoryStore` Protocol, and `InMemoryStore` reference impl.
      Graphiti adapter lands with task 6.
- [~] 1.3 Pin runtime deps incrementally as each phase imports them
      (LLM provider SDKs land with task 3; LangGraph with task 5;
      `graphiti-core` + `neo4j` driver with task 6). Keeps the
      workspace `uv sync` lean and lets each commit's CI green-bar.

## 2. Infra

- [x] 2.1 Neo4j Community 5.26 added to `docker-compose.yml` under
      `agent` profile, with cypher-shell-based healthcheck and
      laptop-friendly heap sizing.
- [x] 2.2 Ollama 0.5 added under `agent` profile. Models are pulled
      at runtime (`docker exec noether-ollama ollama pull llama3.2:3b`)
      rather than baked into the image — keeps the build fast and the
      model choice configurable via `OLLAMA_MODEL`.
- [x] 2.3 `chat_sessions` table added to `noether_storage.schema`
      (raw SQL DDL like the other tables, no Alembic per the existing
      pattern). Picked up by the migrator on next compose up.

## 3. LLM provider abstraction

- [x] 3.1 `make_provider(AgentSettings)` factory routes on `LLM_BACKEND`.
- [x] 3.2 `OllamaProvider` over httpx (`/api/chat`, non-streaming, with
      `format=json` for json_mode). Streaming variant lands with task 7
      (SSE `/chat`).
- [~] 3.3 Cloud providers (OpenAI / Anthropic / Gemini): factory raises
      `NotImplementedError` with install hint until each adapter +
      optional dep extra is added. Tests pin the contract.
- [x] 3.4 `MockProvider` (records calls; deterministic queue) +
      `httpx.MockTransport`-backed `OllamaProvider` tests.

## 4. Tools (`ToolResult` shape)

`ToolResult { summary, data, citations, vega_spec }` + `AgentTool`
runtime-checkable Protocol shipped first; tools land in two waves to
keep dep churn bounded:

- [x] 4.1 `SqlTool` — wraps `libs/storage.latest_value` and
      `range_query`; helpers constructor-injected so tests run without
      Postgres. The wide `pivot` is intentionally not exposed (forecast
      / anomaly tools own that path upstream).
- [x] 4.2 `RagTool` — calls `libs/rag.retrieve` via `asyncio.to_thread`.
      Citations are `doc_id:chunk_idx`; full chunk text is in `data`,
      summary previews are bounded so the synthesiser doesn't drown in
      walls of text.
- [x] 4.3 `MultimodalRagTool` — same base as `RagTool` with distinct
      `name` + `description` so the router can dispatch P&ID intents
      explicitly. Expects to be wired to a retrieve_fn bound to the
      OpenCLIP multimodal Qdrant collection.
- [x] 4.4 `ForecastTool` — HTTP to `services/inference` `/forecast`,
      returns `point` / `lower` / `upper` / `model_kind` in `data`.
- [x] 4.5 `AnomalyTool` — HTTP to `/anomaly` and (optional) `/explain`;
      surfaces top-3 SHAP-blended contributions in the summary.
- [x] 4.6 `VizTool` — emits a Vega-Lite v5 line-chart spec from one or
      more named time series; pure dict construction, no external dep.

## 5. LangGraph orchestrator

- [x] 5.1 `RouterNode` — LLM-as-classifier with json_mode, code-fence
      tolerance, one retry on malformed JSON, `sql` fallback. Bounded
      to `max_tools=3` per turn.
- [x] 5.2 `FanOutNode` — `asyncio.gather` over selected tools with
      `return_exceptions=True` semantics (failed tools log + drop, do
      not poison siblings). Per-tool input filled by `ParamExtractor`,
      which validates LLM JSON against each tool's `input_model`.
- [x] 5.3 `SynthesiserNode` — composes answer, dedupes citations
      preserving order, picks first non-None vega_spec. Tool result
      payloads truncated at 1500 chars in the prompt to fit local-LLM
      context windows; original results remain untouched in state.
- [x] 5.4 `MemoryWriterNode` — extracts JSON facts, persists via the
      `MemoryStore` Protocol, swallows store exceptions to keep the
      chat turn alive. Graphiti adapter slots in behind the same
      Protocol with task 6.
- [x] 5.5 `build_graph(...)` — LangGraph StateGraph wiring all four
      nodes linearly: START → router → fan_out → synthesiser →
      memory_writer → END. Compiles into a single `ainvoke({...})`
      entrypoint that the `/chat` endpoint (task 7) will drive.

## 6. Memory

- [x] 6.1 `MemoryStore.write_facts(session_id, facts)` is async on the
      Protocol; `GraphitiStore` impl serialises each `MemoryFact` as
      a tagged episode (`[session=...] (subject) (predicate) (object)`)
      and calls graphiti-core's `add_episode` with `reference_time =
      fact.t_valid`. Per-fact failures are logged but never propagate
      — write failure must not break the chat turn.
- [x] 6.2 `MemoryStore.retrieve(session_id, query, k)` tags the query
      with the same `[session=...]` prefix so Graphiti's vector
      search focuses on the active session, then maps EntityEdge
      results back to `MemoryFact`s best-effort. Search failure
      degrades to "no memories" rather than raising.
- [x] 6.3 The bound is enforced at the `InMemoryStore` (and graphiti's
      own retention controls govern the persistent store); the
      Protocol stays bound-agnostic so per-backend retention policy
      can vary.

## 7. API

- [x] 7.1 `POST /chat` JSON mode — auth via `X-API-Key`, `ChatRequest`
      / `ChatResponse` Pydantic models. Compiled graph dependency-
      injected via `Depends(get_graph)` so tests override without
      standing up backends. Returns 503 if no graph wired.
- [~] 7.2 `POST /chat` SSE stream — deferred. Requires reshaping the
      orchestrator to yield intermediate events (per-tool results
      + token-level synth output). Out of scope for the v0.1 demo,
      which polls for the JSON response. Wire frame stays open.
- [x] 7.3 Structlog already wires service tag; per-request log lines
      emit `session_id`, `question_len`, `selected_tools`,
      `n_citations`, `has_chart`, `facts_written` via the chat
      router.

## 8. Prompts

- [x] 8.1 Router prompt (intent → tool list) — `prompts/router.md`,
      loaded via `load_prompt("router")`.
- [x] 8.2 Synthesiser prompt (answer + citations + viz) —
      `prompts/synthesiser.md`. `prompts/param_extractor.md` covers the
      per-tool input extraction the synth path depends on.
- [x] 8.3 Fact-extraction prompt for memory writer —
      `prompts/memory_writer.md`, consumed by `MemoryWriterNode`.

## 9. Tests

- [x] 9.1 Unit: router selects expected tools for canned messages
      (`test_orchestrator_router.py`, 9 tests).
- [x] 9.2 Unit: every tool returns valid `ToolResult` for happy path
      across the 6 tool modules + the orchestrator E2E test.
- [x] 9.3 Integration scaffold: `tests/test_integration.py` hits
      `/chat` against a live `docker compose --profile agent up -d`
      stack. Marked `@pytest.mark.integration`, skipped unless
      `AGENT_INTEGRATION_BASE_URL` is set.
- [~] 9.4 Memory continuity test stub present in
      `test_chat_session_continuity_writes_facts`; tightening
      to assert "turn 2 sees turn 1's fact" requires the memory
      retriever node (flagged as follow-up).
- [x] 9.5 86 unit tests on services/agent + 16 on libs/memory; chunked
      Windows pytest workaround; CI on Linux runs them all in one go.
      Coverage ratchet stays at the workspace `fail_under = 35`.

## 10. Observability

- [x] 10.1 `agent_chats_total{status}` counter, incremented from the
      /chat handler — ok / error labels.
- [x] 10.2 `agent_chat_latency_ms` histogram with industrial-AI-relevant
      buckets (50ms .. 60s; local LLM cost dominates).
- [x] 10.3 `agent_tool_calls_total{tool}` counter, one inc per tool
      actually dispatched in fan-out (post router filter). Lets
      dashboards show tool mix and detect "router stopped picking
      RAG"-style regressions.
- [x] 10.4 `GET /metrics` exposition route via `prometheus-client`.
      First service to actually wire Prometheus exporters per CLAUDE.md
      ("Prometheus exporters from every service" rule).

## 11. Air-gap

- [x] 11.1 `OFFLINE_MODE=1` is the default in `AgentSettings`, the
      compose-`agent` profile inherits it via `x-common-env`, and the
      Dockerfile pulls only Python wheels at build time. Once the
      Ollama model is pulled (`docker exec ollama pull <model>`), the
      end-to-end stack runs against zero outbound DNS. Verified by
      reading the network logs of `docker compose --profile agent
      up -d` after the one-time model warm.

## 12. Docs

- [x] 12.1 `services/agent/README.md` rewritten — full architecture
      ASCII diagram, /chat shape with example request/response, env
      vars table, run + test instructions, failure-mode policy
      enumerated.
- [x] 12.2 `libs/memory/README.md` already has the surfaces; updates
      to match the async Protocol shape land here too.
- [x] 12.3 `docs/architecture.md` extended with the missing RAG section
      (M3 Phase 1+2 surfaces) and the new Agent system section
      (LangGraph topology, node responsibilities, provider/memory
      abstractions).
