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

- [ ] 2.1 Add Neo4j Community to `docker-compose.yml` with healthcheck
- [ ] 2.2 Add Ollama container with `llama3.3:8b-instruct` pre-pulled
      via init container
- [ ] 2.3 `chat_sessions` Alembic migration in storage repo

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

- [ ] 6.1 `libs/memory.write_facts(session_id, facts)`
- [ ] 6.2 `libs/memory.retrieve(session_id, query, k)`
- [ ] 6.3 Bound memory to the most recent 200 facts per session

## 7. API

- [ ] 7.1 `POST /chat` JSON mode
- [ ] 7.2 `POST /chat` SSE stream mode
- [ ] 7.3 Trace id, request id, latency on every log line

## 8. Prompts

- [ ] 8.1 Router prompt (intent → tool list)
- [ ] 8.2 Synthesiser prompt (answer + citations + viz)
- [ ] 8.3 Fact-extraction prompt for memory writer

## 9. Tests

- [ ] 9.1 Unit: router selects expected tools for canned messages
- [ ] 9.2 Unit: tool returns valid `ToolResult` for happy path
- [ ] 9.3 Integration: docker compose stack, demo query returns
      contributing tags + citation + viz spec
- [ ] 9.4 Memory: turn 2 of a session sees turn-1 fact in trace
- [ ] 9.5 Coverage >=70% on `services/agent/` and `libs/memory/`

## 10. Observability

- [ ] 10.1 Counter `agent_chats_total{status}`
- [ ] 10.2 Histogram `agent_chat_latency_ms`
- [ ] 10.3 Counter `agent_tool_calls_total{tool}`

## 11. Air-gap

- [ ] 11.1 With `LLM_BACKEND=ollama` and `OFFLINE_MODE=1`, end-to-end
      query succeeds with no external DNS

## 12. Docs

- [ ] 12.1 `services/agent/README.md`: env vars, providers, prompts
- [ ] 12.2 `libs/memory/README.md`: Graphiti facts API
- [ ] 12.3 Agent section added to `docs/architecture.md`
