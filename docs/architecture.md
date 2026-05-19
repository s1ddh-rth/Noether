# Architecture

See **SPEC section 4** for the canonical diagram. This file annotates the pieces
that exist today and what's stubbed.

## M1 footprint (live)

```
[ ingest ]  →  Redpanda(plant.tags)  →  [ storage-consumer ]  →  TimescaleDB(tag_samples)
                                                                       ↑
                                              [ inference (FastAPI /forecast) ]
                                                                       ↑
                                                                  [ Grafana ]
```

- `services/ingest` — `noether_svc_ingest`. Drives `SyntheticTEP` at
  `REPLAY_HZ`, publishes to `plant.tags` keyed by tag name.
- `services/storage-consumer` — `noether_svc_storage`. Reads `plant.tags`,
  validates `TagSample`, batched `COPY` into `tag_samples`. At-least-once.
- `services/inference` — `noether_svc_inference`. FastAPI app exposing
  `/forecast` backed by per-tag LightGBM artifacts baked into the image
  at build time.

## Storage

`tag_samples (ts, tag, value, quality)` Timescale hypertable, 1-day chunks,
compression after 7d, retention configurable via `RETENTION_DAYS`.

## Forecasting

LightGBM with lag (1, 2, 3, 5, 10, 30, 60 min), rolling mean/std (5, 15, 60 min),
and hour-of-day cyclical features. Forecast horizon defaults to 30 minutes.
Prediction interval is currently `±1.96σ` of validation residuals — quantile
regression / conformal will replace this in a follow-up change.

## RAG (M3 Phase 1+2 — live)

```
PDFs / P&IDs  →  parse → chunk → embed → [Qdrant]  ──┐
                                          [BM25]    ──┤→ RRF (k=60) → BGE-reranker → top-N
                                                     ─┘
```

Two retrieval surfaces share the same `retrieve(query, ...)` entrypoint:

- **Text** — BGE-base dense embeddings + BM25 (lexical) over PDF chunks
  (`source_type=pdf_text`). Cross-encoder rerank (BGE-reranker-base) lifts
  semantic precision on the RRF top-K=20 → top-N=5.
- **Multimodal P&ID** — OpenCLIP ViT-B/32 in a single shared embedding
  space (the BGE-M3 path was dropped — text-only model; see
  `openspec/changes/archive/2026-05-01-add-rag-pipeline/design.md` errata).
  Page-render via pypdfium2; query-time text encoding hits OpenCLIP's text
  branch so cross-modal text → image retrieval works without a captioning
  hop.

`retrieve()` accepts a list of `QdrantIndex | (QdrantIndex, Embedder)`
tuples so the multimodal collection uses its own encoder while the text
collection keeps `BgeTextEmbedder`. Both rankings still merge through RRF
unchanged.

Idempotent ingest: `doc_id = sha256(file_bytes)`, point id =
`uuid5(doc_id, chunk_idx)` so re-ingesting an unchanged file is a no-op.
Cross-run dedup tracked via the BM25 pickle (text path) or via Qdrant
payload scroll (multimodal path).

## Agent system (M3 — live)

```
[ /chat ]  →  router  →  fan_out (parallel tools)  →  synthesiser  →  memory_writer
                │                  │                       │                │
                ▼                  ▼                       ▼                ▼
           LLM-as-classifier   {sql, rag, mm-rag,         LLM           Graphiti
           (json_mode +        forecast, anomaly,         compose       (Neo4j-
           code-fence          viz}                       answer +      backed)
           tolerance)          each behind                citations
                               AgentTool Protocol         + vega_spec
```

`services/agent` runs the LangGraph StateGraph behind FastAPI `POST /chat`.
Each node mutates a strict subset of the shared `ChatState` TypedDict:

- **Router** — LLM picks 1-3 tools from the registered set in strict JSON.
  Bounded retries + `sql` fallback so a malformed response never breaks the
  turn.
- **Fan-out** — `asyncio.gather` over the selected tools. Each branch runs
  the `ParamExtractor` (LLM-driven JSON → validated Pydantic input model)
  then dispatches `tool.run(input)`. Sibling failures don't cascade.
- **Synthesiser** — composes the answer; aggregates `citations` deduped
  preserving order; first non-None `vega_spec` wins. Tool result payloads
  truncated at 1500 chars in the prompt to fit local-LLM context windows.
- **Memory writer** — extracts `MemoryFact` triples from the turn and
  persists via the `MemoryStore` Protocol. Best-effort: parse / store
  failure → 0 facts written, never raises.

LLM provider abstraction (`Provider` Protocol): `OllamaProvider` (local
default, air-gapped path) and `MockProvider` (deterministic stub for
tests). Cloud backends (OpenAI / Anthropic / Gemini) raise
`NotImplementedError` with install hint until the optional SDK extras
are wired up.

Memory backend: `GraphitiStore` serialises each fact as a tagged episode
(`[session=<id>] (subject) (predicate) (object)`) into Graphiti's
`add_episode`, then reverse-engineers `MemoryFact`s from the
`EntityEdge` results. Per-session scoping via the `[session=...]` tag.

## Frontend (add-frontend-dashboard — live)

Next.js 14 App Router (`services/frontend`, TypeScript + Tailwind,
pnpm). Two routes:

- `/dashboard` — a grid of `<TagTile>` (tag id, value, Recharts
  5-min sparkline, `data-stale` >30 s) + an `<AnomalyPanel>`. SWR
  polling: tags 1 s, anomalies 5 s, per-tile range 15 s.
- `/chat` — operator chat: per-tab `session_id` (sessionStorage),
  message list, citations footer, and `<VegaChart>` (lazy
  `vega-embed`, wrapped in an `<ErrorBoundary>`; malformed specs fall
  back to a message + raw-spec `<details>`).

**BFF.** Route handlers under `app/api/*` keep all backend access
server-side. Tag/anomaly endpoints query TimescaleDB directly via a
pooled `pg` client (`lib/db.ts`, `server-only`); `/api/chat` proxies
to `services/agent` injecting `X-API-Key` server-side. The browser
only ever sees the shaped JSON in `lib/types.ts` — no DB creds, no
agent key. Air-gapped: self-hosted Geist fonts (`next/font/local`),
no Google Fonts / CDN; standalone Docker output.

The agent is JSON-only today; the chat client + proxy are structured
so SSE slots in when the agent gains streaming (see below).

## Out of M3 (planned)

- SSE streaming on `/chat` (orchestrator needs to yield intermediate
  events; deferred from v0.1) — the frontend already tolerates it
- Memory retriever node (pull prior facts into state at session entry)
- Prometheus exporters in every service (M4 — agent has them now)
- MLflow model registry (M4)
- Grafana dashboards beyond the starter `plant-tags` board (M4)
- Real Tennessee Eastman simulator (later, behind a change proposal)
