# services/agent

LangGraph-orchestrated chat service. Routes operator questions through a
classifier, fans out to specialised sub-agents (SQL, RAG, multimodal RAG,
forecast, anomaly, viz) in parallel, and synthesises the answer with
citations and an optional Vega-Lite chart. Memory writes go through
`libs/memory`.

## Endpoints

| Path | Auth | Notes |
|---|---|---|
| `GET /healthz` | none | liveness probe |
| `POST /chat` | `X-API-Key` | JSON or SSE; coming in a later phase |

## Env vars

| Var | Default | Notes |
|---|---|---|
| `AGENT_HOST` | `0.0.0.0` | |
| `AGENT_PORT` | `8100` | distinct from inference's 8000 |
| `AGENT_API_KEY` | `changeme-please` | |
| `LLM_BACKEND` | `ollama` | `ollama` (default) / `openai` / `anthropic` / `gemini` |
| `OFFLINE_MODE` | `1` | enforces Ollama-only when truthy |
| `LOG_LEVEL` | `info` | |

## Run

```
docker compose --profile agent up -d agent
curl http://localhost:8100/healthz
```

## Test

```
uv run pytest services/agent
```
