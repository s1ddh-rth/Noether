# services/agent

LangGraph-orchestrated chat service. Routes operator questions through a
classifier, fans out to specialised sub-agents (SQL, RAG, multimodal RAG,
forecast, anomaly, viz) in parallel, and synthesises the answer with
citations and an optional Vega-Lite chart. Memory writes go through
`libs/memory` (Graphiti + Neo4j in production, in-memory in tests).

## Architecture

```
┌──────────────┐
│   /chat      │  POST { session_id, question }
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                LangGraph StateGraph                          │
│                                                              │
│  router  →  fan_out  →  synthesiser  →  memory_writer        │
│   (LLM)    (parallel    (LLM)            (LLM + Graphiti)    │
│            tools)                                            │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
   { answer, citations, vega_spec, selected_tools, facts_written }
```

Each node is a thin async fn unit-testable in isolation. The full pipeline is
exercised end-to-end with mocks in `tests/test_orchestrator_graph.py`; the
docker-compose `agent` profile wires it to live Ollama + Neo4j + Qdrant +
Postgres + the inference service.

## Endpoints

| Path | Auth | Notes |
|---|---|---|
| `GET /healthz` | none | liveness probe |
| `GET /metrics` | none | Prometheus exposition (chats, latency, tool counts) |
| `POST /chat` | `X-API-Key` | runs the orchestrator; returns answer + citations |

### `POST /chat`

Request:
```json
{
  "session_id": "operator-jane-2026-05-01",
  "question": "Why did the FT-101 alert fire yesterday at 14:23?"
}
```

Response:
```json
{
  "session_id": "operator-jane-2026-05-01",
  "answer": "FT-101 alert was a calibration drift [manual-1:0].",
  "citations": ["manual-1:0"],
  "vega_spec": null,
  "selected_tools": ["anomaly", "rag"],
  "facts_written": 1
}
```

`vega_spec` is non-null when the router includes the `viz` tool — frontends
should render it directly via Vega-Lite v5.

## Env vars

| Var | Default | Notes |
|---|---|---|
| `AGENT_HOST` | `0.0.0.0` | |
| `AGENT_PORT` | `8100` | distinct from inference's 8000 |
| `AGENT_API_KEY` | `changeme-please` | |
| `LLM_BACKEND` | `ollama` | `ollama` (default) / `openai` / `anthropic` / `gemini` |
| `OLLAMA_HOST` | `http://localhost:11434` | `http://ollama:11434` inside compose |
| `OLLAMA_MODEL` | `llama3.2:3b-instruct` | tag must be pulled before first use |
| `QDRANT_URL` | `http://localhost:6333` | |
| `NEO4J_URI` | `bolt://localhost:7687` | |
| `NEO4J_USER` / `NEO4J_PASSWORD` | `neo4j` / `noetherpw` | |
| `INFERENCE_URL` | `http://localhost:8000` | for forecast/anomaly tools |
| `INFERENCE_API_KEY` | `changeme-please` | |
| `OFFLINE_MODE` | `1` | enforces no outbound DNS |
| `LOG_LEVEL` | `info` | |

## Run

```sh
# 1) Bring up the full stack (~3 min first build):
docker compose --profile agent up -d

# 2) One-time: pull the Ollama model:
docker exec -it noether-ollama ollama pull llama3.2:3b

# 3) Hit /chat:
curl -X POST http://localhost:8100/chat \
  -H "X-API-Key: changeme-please" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","question":"What is FT-101 right now?"}'
```

## Test

```sh
# Unit (no infra needed — full mocks):
uv run pytest services/agent

# Integration (requires `docker compose --profile agent up -d` first):
uv run pytest -m integration services/agent
```

## Failure-mode policy

The orchestrator is structured so a single bad LLM response **never** breaks a
chat turn:

- **Router** malformed JSON: one retry with stricter system message, then
  fallback to `["sql"]`.
- **Param extractor** parse / validation failure: returns `None`; that tool is
  skipped.
- **Fan-out** unknown tool / failed input / runtime exception: drops that
  branch, lets siblings continue (`asyncio.gather` with caught exceptions).
- **Synthesiser** empty tool results: still calls the LLM; prompt instructs
  honest "I don't have data".
- **Memory writer** parse / store failure: logs, returns 0, never raises.

Each is pinned by a unit test.
