# Noether — Project Specification

> **An open-source reference architecture for industrial AI copilots.**
> Real-time anomaly detection, forecasting, and natural-language reasoning over plant data — physics-grounded, air-gappable, deployable on a laptop or a k3s cluster.

---

## 0. Meta — How To Use This File

This is the **canonical spec**. Everything in this file is the source of truth. If conversation, code, or commits drift from it, this file wins. Update it deliberately when scope changes; do not silently diverge.

You are an AI coding agent (Claude Code) collaborating with the human author on this project. Your job is to **propose changes before implementing them**. Do not invent architecture. Do not pick libraries that aren't named here without explicitly proposing an addition first.

**On first read of this file, your immediate next steps are:**

1. Read this file fully.
2. Generate a `CLAUDE.md` at the repo root capturing the conventions in section 7 below, in the standard CLAUDE.md format used by Anthropic's Claude Code.
3. Initialise OpenSpec in the repo. Generate one OpenSpec change proposal per component listed in section 4 (eight proposals total). Do NOT implement them yet — just create the proposals so the human can review.
4. Once proposals exist, await human approval before implementing anything.
5. The very first implementation milestone is **Milestone 1** in section 8. Do not skip ahead.

If anything in this file is ambiguous, ask before assuming.

---

## 1. Project Goals

Noether is a portfolio-grade open-source project demonstrating production engineering for industrial AI. It must:

- **Run end-to-end on a laptop** in under 60 seconds via `docker compose up`
- **Deploy to k3s/k3d** via a single Helm chart, production-style
- **Operate fully air-gapped** when configured to use a local Ollama LLM backend
- **Demonstrate every capability** named in section 3, with benchmark evidence
- Be **clearly documented** enough that a hiring manager can clone, run, and understand it inside ten minutes
- Be **legibly architected** enough to discuss confidently in a senior interview

Non-goals: this is not a startup. It is not competing with TDengine, Cognite, or AspenTech. The novelty is **integration, eval rigour, and the deployment story** — not new ML algorithms.

---

## 2. Target Audience For This Repo

Two audiences; both must be served by the README:

1. **Hiring managers** at Applied Computing, Whalar/Foam, OpenAI FDE, Palantir, Databricks FDE, and similar — engineering leaders evaluating senior ML/forward-deployed candidates
2. **Learners** wanting a clean, working reference for industrial AI, RAG, multi-agent systems, time-series ML, MLOps

If a design choice splits these audiences, prioritise audience 1. Where it doesn't, write for audience 2 (better docs, friendlier defaults).

---

## 3. Capabilities (What Noether Does)

1. **Ingests** simulated plant sensor data via Kafka (Redpanda) at ~1 Hz across ~50 tags
2. **Stores** the time-series in TimescaleDB as a hypertable
3. **Forecasts** key process variables 30 minutes ahead using an ensemble of LightGBM and PatchTST
4. **Detects anomalies** using a multivariate stack: Isolation Forest, autoencoder, Mahalanobis distance, EWMA control charts
5. **Explains** detected anomalies using SHAP, with results routed through an LLM agent for natural-language summary
6. **Answers** operator questions in natural language via a LangGraph multi-agent system that can query the time-series DB, search documentation (RAG), look up P&ID context (multimodal RAG), trigger forecasts, run anomaly checks on demand, and generate visualisations
7. **Remembers** across sessions via Graphiti — a temporal knowledge graph capturing operator queries, equipment state changes, threshold tunings, and cross-shift context
8. **Monitors itself** — drift detection on inputs and predictions, RAG groundedness scores, latency SLOs — all visible in Grafana
9. **Deploys** via Docker Compose (dev) or a Helm chart on k3s (prod-style); switches to fully offline operation via a single config flag

---

## 4. Architecture & Components

```
┌─────────────────┐
│ Data Replayer   │  pyTEP / SKAB / NASA CMAPSS
└────────┬────────┘
         │ JSON
         ▼
┌─────────────────┐
│ Redpanda (Kafka)│  topic: plant.tags
└────────┬────────┘
         │
         ├──────────────────┐
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│  TimescaleDB    │  │  Inference API  │
│  hypertables    │  │  FastAPI        │
└────────┬────────┘  │   /forecast     │
         │           │   /anomaly      │
         │           │   /explain      │
         │           └────────┬────────┘
         │                    │
         │                    ▼
         │            ┌─────────────────┐
         │            │ Alert Manager   │ ─► Grafana
         │            │ + Drift Monitor │
         │            └─────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│      LangGraph Multi-Agent Orchestrator      │
│                                              │
│  Router ─┬─► SQL Agent (Timescale)           │
│          ├─► RAG Agent (Qdrant)              │
│          ├─► Multimodal RAG Agent (P&IDs)    │
│          ├─► Forecast Agent → Inference      │
│          ├─► Anomaly Agent → Inference       │
│          └─► Viz Agent (Vega-Lite)           │
│                                              │
│  Memory: Graphiti (Neo4j-backed)             │
│  LLM:    Ollama | OpenAI | Claude | Gemini   │
└──────────────────┬───────────────────────────┘
                   ▼
        ┌─────────────────────┐
        │  Next.js Frontend   │
        │  /dashboard /chat   │
        └─────────────────────┘

Observability: Prometheus + Grafana
Eval:          RAGAS + custom forecast/AD harness
Versioning:    MLflow + DVC
CI/CD:         GitHub Actions
```

The eight components, each of which becomes one OpenSpec change proposal:

1. **Ingest** — pyTEP replayer, Redpanda producer, schema definitions, replay-rate control
2. **Storage** — TimescaleDB schema, hypertables, compression policy, retention
3. **Forecasting** — LightGBM and PatchTST training pipeline, ensemble logic, FastAPI `/forecast` endpoint, eval harness
4. **Anomaly Detection** — PyOD-based ensemble (Isolation Forest, autoencoder, Mahalanobis, EWMA), streaming inference loop, FastAPI `/anomaly` endpoint, SHAP explainability
5. **RAG** — Document ingestion (PDF parsing), chunking, BGE embeddings, Qdrant indexing, hybrid search (vector + BM25), cross-encoder reranking, RAGAS evaluation
6. **Agent System** — LangGraph orchestrator with router and six sub-agents, Graphiti memory integration, Ollama/cloud LLM dual-mode, prompt templates
7. **Frontend** — Next.js dashboard with live tag display, anomaly feed, chat interface; minimal design — Recharts for plots, Vega-Lite for agent-generated charts
8. **Ops** — Docker Compose dev stack; Helm chart for k3s; Prometheus exporters from every service; Grafana dashboards; drift monitoring via Evidently; CI/CD via GitHub Actions

---

## 5. Tech Stack — Locked Choices

These are decided. Do not propose alternatives unless explicitly asked.

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11 | One version, pinned via `uv` |
| Package manager | `uv` | Faster than pip; lockfile committed |
| Async framework | FastAPI | All inference services |
| ML framework | PyTorch (DL) + scikit-learn / LightGBM (classical) | No TensorFlow, no Keras |
| Forecasting libs | Nixtla `neuralforecast` (PatchTST) + native LightGBM | Don't reimplement |
| Anomaly libs | PyOD primary, scikit-learn fallback | Don't reimplement |
| Streaming | Redpanda (Kafka API-compatible) | Lighter than Confluent Kafka |
| TS database | TimescaleDB | Postgres extension; familiar SQL |
| Vector DB | Qdrant | Self-hosted, OSS |
| Graph DB | Neo4j Community | For Graphiti memory backend |
| Agent memory | Graphiti (Apache 2.0) | Zep's OSS engine |
| Agent orchestration | LangGraph | OSS |
| Embeddings | BGE-base (local) or BGE-M3 | No paid embedding APIs in default config |
| Reranker | BGE-reranker-base | Cross-encoder, local |
| LLM (default) | Ollama with Llama 3.3 / Qwen 2.5 | Air-gapped path |
| LLM (optional) | OpenAI / Claude / Gemini | Behind a config flag |
| Drift monitoring | Evidently AI (OSS) | Self-hosted |
| Eval | RAGAS for RAG; custom harness for forecast/AD | |
| Experiment tracking | MLflow (self-hosted) | |
| Data versioning | DVC | Remote = local disk by default |
| Frontend | Next.js 14 + TypeScript + Tailwind + Recharts | App Router |
| Observability | Prometheus + Grafana | Both self-hosted |
| Container runtime | Docker | |
| K8s distribution | k3s (via k3d for local) | Industrial edge story |
| K8s packaging | Helm 3 | One chart |
| CI/CD | GitHub Actions | Free for public repos |
| Container registry | GHCR | Free for public images |
| Secrets in dev | `.env` files (gitignored) | |
| Secrets in k3s | Kubernetes Secrets, no SealedSecrets needed for portfolio |

**Air-gap rule:** every component must work with `LLM_BACKEND=ollama` and zero outbound network calls. Cloud LLMs are an option, never a requirement.

**Cost rule:** the entire stack must run with zero paid services. No exceptions in the default config.

---

## 6. Datasets

All public, all open, all commit-clean:

| Dataset | Use | Licence |
|---|---|---|
| Tennessee Eastman Process (pyTEP) | Primary forecasting + anomaly detection benchmark | Public domain |
| SKAB (Skoltech Anomaly Benchmark) | Real industrial AD validation | MIT |
| NASA CMAPSS | Optional RUL / predictive maintenance demo | Public domain |
| NASA tech reports + DOE process safety docs | RAG corpus | Public domain |
| Synthetic P&IDs from `draw.io` templates | Multimodal RAG corpus | Self-generated, MIT in repo |

No private data, no scraped data, no NDA-encumbered data. Period.

---

## 7. Conventions (Source of Truth for CLAUDE.md)

Every convention below must be reflected in the generated `CLAUDE.md`.

### Code style
- Python: Black (line length 100), Ruff for linting, mypy strict on new code
- TypeScript: Prettier, ESLint (Next.js defaults), strict mode in `tsconfig.json`
- Pre-commit hooks via `pre-commit`: black, ruff, mypy, prettier, eslint, end-of-file-fixer, trailing-whitespace
- No `print()` in production code — use `structlog` for structured JSON logs

### Project structure
```
noether/
├── SPEC.md                    # this file
├── CLAUDE.md                  # conventions for Claude Code
├── README.md                  # public-facing
├── pyproject.toml             # uv-managed
├── docker-compose.yml         # dev stack
├── charts/noether/            # Helm chart
├── services/
│   ├── ingest/                # pyTEP replayer
│   ├── inference/             # FastAPI: forecast, anomaly, explain
│   ├── agent/                 # LangGraph orchestrator
│   └── frontend/              # Next.js
├── libs/
│   ├── forecasting/           # shared forecast logic
│   ├── anomaly/               # shared AD logic
│   ├── rag/                   # ingestion, chunking, retrieval
│   └── memory/                # Graphiti wrapper
├── eval/
│   ├── forecast_harness.py
│   ├── anomaly_harness.py
│   └── rag_ragas.py
├── data/                      # DVC-tracked, not committed
├── notebooks/                 # exploratory only — not part of the runtime
└── docs/
    ├── architecture.md
    ├── benchmarks.md
    └── deployment.md
```

### Testing
- Pytest for Python; minimum 70% coverage on new code in `libs/` and `services/`
- Vitest for the Next.js frontend
- Integration tests use `docker compose up -d` with health-checked services
- No tests = no merge

### Commits and branches
- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`)
- One branch per OpenSpec change proposal: `change/<proposal-slug>`
- PRs require: green CI, updated docs if behaviour changes, eval results in PR description if a model is touched

### Configuration
- All config via `pydantic-settings` `BaseSettings`
- `.env.example` committed, `.env` gitignored
- One `values.yaml` for the Helm chart, with `values.dev.yaml` and `values.airgapped.yaml` overlays

### Library discipline
- **Use OSS, do not reimplement.** PyOD for anomaly detection. Nixtla for forecasting. Graphiti for memory. RAGAS for eval. If you find yourself writing more than 30 lines of "core algorithm," stop and ask whether a library does it
- Adding a new top-level dependency requires an OpenSpec change proposal, not a silent `uv add`

### Logging and errors
- structlog for Python, JSON output
- Every FastAPI endpoint emits `request_id`, `latency_ms`, `status`
- No bare `except:` — always specify exception types
- Errors that cross service boundaries are typed (Pydantic models)

### Security
- No API keys in code, ever
- No data with PII in commits
- Air-gapped mode must work without any external DNS lookups (`OFFLINE_MODE=1` env flag enforces this)

### Documentation
- Every service has a `README.md` covering: purpose, endpoints, env vars, how to run, how to test
- Architecture diagrams kept as `.mermaid` source in `/docs`, rendered to SVG in CI
- The top-level `README.md` is rewritten only via PR — not touched casually

---

## 8. Milestones (Build Order)

Each milestone is a hard deliverable. Do not start the next until the prior is demoable. Each milestone corresponds to a week of evening/weekend work.

### Milestone 1 — Foundation (Week 1)
**Deliverable:** `docker compose up` brings up Redpanda, TimescaleDB, Grafana, and a pyTEP replayer streaming live to the DB. A FastAPI service exposes a baseline LightGBM `/forecast` endpoint against TEP data. Forecast eval harness runs and prints MAE/RMSE.

### Milestone 2 — Anomaly Detection + Explainability (Week 2)
**Deliverable:** Streaming AD ensemble (Isolation Forest + autoencoder + Mahalanobis + EWMA) consumes from Redpanda and emits scored events. SHAP explanations attached to alerts. Anomaly eval harness runs against TEP fault scenarios; precision/recall/F1 written to `docs/benchmarks.md`.

### Milestone 3 — RAG + Agent System (Week 3)
**Deliverable:** Qdrant indexed with the public RAG corpus. Hybrid search + reranker working. LangGraph orchestrator with router and six sub-agents. Graphiti memory persisting across sessions. Ollama backend working air-gapped. A demo query — *"Why did anomaly fire on FT-101 yesterday at 14:23?"* — returns a complete answer with citations and an embedded chart.

### Milestone 4 — Production Polish (Week 4)
**Deliverable:** Helm chart deploys cleanly to k3d. Drift monitoring (Evidently) running. MLflow tracking all models. GitHub Actions CI/CD building and pushing images to GHCR. README finalised with hero GIF, architecture diagram, benchmarks, quickstart, and a 3-minute Loom demo video linked.

After Milestone 4, the repo is "v0.1.0" and ready to share.

---

## 9. Out Of Scope (For v0.1)

These are explicitly *not* being built. Do not propose them.

- Real OPC UA / SCADA / DCS connectors (the JD mentions these, but the simulated stream is sufficient evidence)
- Custom physics-informed neural networks (PINNs) — physics constraints are mentioned conceptually but not implemented as a custom layer
- Fine-tuned domain LLMs (we use prompt-engineered general models)
- Cloud-managed K8s (EKS/GKE) — k3d/k3s only, by design
- Multi-tenant deployments
- Authentication beyond a basic API key on the inference endpoints
- Mobile or responsive frontend beyond what Tailwind gives for free
- Real-time websocket streaming to the frontend (poll-based is fine for v0.1)
- Custom embedding model training
- Anything requiring a paid API key in default mode

These can become v0.2 issues after the core ships.

---

## 10. Definition Of Done (v0.1.0)

Tick every box. No exceptions.

- [ ] `docker compose up` works on a clean machine in <60s after image pull
- [ ] `helm install noether ./charts/noether` deploys cleanly to k3d
- [ ] Air-gapped mode (`LLM_BACKEND=ollama`, `OFFLINE_MODE=1`) works end-to-end
- [ ] Forecast benchmark: MAE table for at least 3 TEP variables vs. naive/ARIMA/LightGBM/PatchTST published in `docs/benchmarks.md`
- [ ] AD benchmark: precision/recall/F1 across at least 5 TEP fault scenarios published
- [ ] RAG benchmark: RAGAS faithfulness, answer relevancy, context precision published
- [ ] CI green on `main`; no failing tests; coverage ≥70% on `libs/` and `services/`
- [ ] README has: 1-line tagline, hero GIF, architecture diagram, quickstart, capabilities list, benchmarks, deployment guide, roadmap
- [ ] 3-minute Loom video demo embedded in README
- [ ] All eight components have a service-level README
- [ ] License: Apache 2.0 (`LICENSE` file at root)
- [ ] CONTRIBUTING.md exists (even if minimal)
- [ ] Tag `v0.1.0` cut on `main`

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Scope creep | This file. Strict adherence to section 4 and section 9. Any addition is an OpenSpec change proposal |
| Time overrun | If a milestone slips by more than 3 days, cut scope from section 3, do not extend the milestone |
| Library churn | Lock versions in `pyproject.toml`. Renovate bot off until v0.1 ships |
| LLM cost creep | Default to Ollama. CI does not call cloud LLMs. Smoke-test cloud paths manually |
| Over-engineering | "Boring tech wins" — see section 5 stack. No service mesh, no operators, no CRDs |
| Documentation lag | Docs updated in the same PR as the code change. Reviewers reject PRs without doc updates |

---

## 12. Glossary (For The Agent's Benefit)

- **Tag** — a single sensor channel (e.g., `FT-101.PV` = process value of flow transmitter 101)
- **Historian** — time-series database storing plant tag data
- **DCS** — Distributed Control System; brain controlling plant operations
- **OPC UA** — dominant industrial comms protocol
- **P&ID** — Piping & Instrumentation Diagram
- **Setpoint** — target value an operator drives a variable to
- **Air-gapped** — disconnected from public internet, common in OT environments
- **TEP** — Tennessee Eastman Process, the standard simulated chemical-plant benchmark
- **PINN** — Physics-Informed Neural Network
- **SHAP** — SHapley Additive exPlanations, a model interpretability method
- **Drift** — when production data distribution diverges from training distribution

---

## 13. The Author's Operating Posture

The human author is a mid-career ML engineer building Noether as both a portfolio piece and a learning vehicle. He values:

- **Engineering judgement over implementation heroics** — picking the right OSS tool > writing it from scratch
- **Spec-first development** — explicit plan, then code
- **Clear, concise documentation** — an engineer should be able to understand any part of this repo in <10 minutes
- **Honest scoping** — better a small thing that works than a big thing that doesn't

When in doubt, optimise for *clarity* and *shippability*, not cleverness.

---

**End of spec. Now: read it again, generate `CLAUDE.md` from section 7, initialise OpenSpec, generate the eight change proposals from section 4, and stop. Await approval before implementing anything.**
