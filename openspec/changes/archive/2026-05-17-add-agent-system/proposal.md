## Why

The agent system is the user-facing intelligence of Noether: it answers
operator questions, coordinates tools, and persists memory across
sessions (SPEC section 3 (6) and (7)). SPEC section 4 (component 6) names LangGraph
with a router and six sub-agents (SQL, RAG, multimodal RAG, forecast,
anomaly, viz), Graphiti memory on Neo4j, and dual-mode LLM (Ollama
default, cloud optional).

This change is the centrepiece of Milestone 3 (SPEC section 8). The Milestone-3
demo query — *"Why did anomaly fire on FT-101 yesterday at 14:23?"* —
must work end-to-end after this change ships.

## What Changes

- Add `services/agent/` running a LangGraph orchestrator behind FastAPI
  `POST /chat`.
- Add `libs/memory/` wrapping Graphiti against a Neo4j Community
  container.
- Add Neo4j Community to `docker-compose.yml`.
- Implement six sub-agents with shared tool contracts:
  - **SQL** (queries `tag_samples` / `tag_anomalies` via `libs/storage`)
  - **RAG** (calls `libs/rag.retrieve`)
  - **Multimodal RAG** (calls same lib with `source_type=pid_image` filter)
  - **Forecast** (calls `services/inference` `/forecast`)
  - **Anomaly** (calls `/anomaly` and `/explain`)
  - **Viz** (emits Vega-Lite specs the frontend renders)
- LLM provider abstraction: Ollama (default) or OpenAI/Claude/Gemini via
  env flag `LLM_BACKEND`.
- Prompt templates under `services/agent/prompts/`.

## Capabilities

### New Capabilities
- `agent-system`: Route operator questions through a LangGraph
  orchestrator with six tool-calling sub-agents and persistent
  cross-session memory backed by Graphiti.

### Modified Capabilities
_None (all upstream lib APIs are stable contracts owned by their
respective changes)._

## Impact

- New code: `services/agent/` (LangGraph orchestrator, tools, prompts),
  `libs/memory/` (Graphiti wrapper).
- New deps (justified): `langgraph`, `langchain-core` (transitive),
  `graphiti-core`, `neo4j` driver, `httpx` (already implied), provider
  SDKs only loaded conditionally (`ollama`, `openai`, `anthropic`,
  `google-generativeai`).
- New infra: Neo4j Community container in `docker-compose.yml`, Ollama
  container with a default small model pre-pulled.
- Consumed by: `services/frontend` chat surface.
- Out of scope: fine-tuned domain LLMs, custom embeddings (SPEC section 9).
