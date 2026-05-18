# Noether

> **Open-source reference architecture for industrial AI copilots.**
> Real-time anomaly detection, forecasting, and (soon) natural-language
> reasoning over simulated plant data. Physics-grounded, air-gappable,
> deployable on a laptop or a k3s cluster.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](pyproject.toml)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![spec-driven](https://img.shields.io/badge/spec_driven-OpenSpec-7a52f4.svg)](openspec/)

---

## What's in the box (today)

- **Streaming ingest** of 52 plant tags (`XMEAS_1..41` measurements +
  `XMV_1..11` manipulated variables) at 1 Hz over Redpanda.
- **Hypertable storage** in TimescaleDB with compression after 7 days +
  configurable retention (default 90 d).
- **Forecasting** via a `LightGBM + PatchTST` ensemble, served from a
  FastAPI `/forecast` endpoint with model-kind dispatch
  (`.ensemble` &gt; `.patchtst` &gt; `.lgbm` artefacts).
- **Anomaly detection** with a 3-detector ensemble (Isolation Forest +
  robust Mahalanobis + EWMA control chart). Streaming worker scores
  60-s windows every 5 s; results land in the `tag_anomalies` hypertable.
- **Explainability** via SHAP `TreeExplainer` for the IForest member,
  analytic per-tag breakdowns for the others, blended into a single
  ranked attribution returned by `/explain`.
- **Eval harnesses** for forecasting (naive / LGBM / PatchTST / ensemble
  × MAE / RMSE / SMAPE) and anomaly detection (precision / recall / F1
  across six fault scenarios with threshold sweeps).
- **Grafana** auto-provisioned with a starter `Plant Tags` dashboard
  reading directly from Timescale.
- **One command stand-up** — `make up` brings the whole stack online
  in &lt;60 s after image pull.

- **Self-hosted MLflow**, a **Helm chart** (`charts/noether/`) that
  deploys the whole stack to k3d/k3s with dev / air-gapped overlays,
  **Evidently drift monitoring** (CronJob → Grafana), and **CI/CD**
  (lint · type · test · compose smoke · k3d e2e · image build/push).

What's *not* here yet (planned, see [Roadmap](#roadmap)): the Next.js
frontend (`add-frontend-dashboard`), the real Tennessee Eastman
simulator (separate change proposal), torch-backed AutoEncoder detector.

---

## Quickstart

```bash
git clone git@github.com:s1ddh-rth/Noether.git
cd Noether
cp .env.example .env
make up                  # docker compose --profile core up -d
make logs                # tail every service
```

Once everything is healthy:

| What | Where |
|---|---|
| Inference API | http://localhost:8000 (`/healthz`, `/readyz`) |
| Grafana | http://localhost:3000 (admin / admin; `Noether → Plant Tags`) |
| TimescaleDB | `localhost:5432` (db `noether`, user `noether`) |
| Redpanda Kafka | `localhost:9092` |

Run the eval harnesses (forecast and anomaly) once the stack has been
ingesting for a few minutes:

```bash
make eval                # forecast harness — LGBM vs naive (smoke)
docker compose --profile eval run --rm forecast-eval \
    python -m eval.forecast_harness --hours 168   # full 4-model bench
docker compose --profile eval run --rm anomaly-eval
```

Tear down:

```bash
make down                # also drops volumes
```

See [`docs/deployment.md`](docs/deployment.md) for the k3d / air-gapped
path (M4).

---

## Architecture

```
[ ingest ] ──► Redpanda(plant.tags) ──► [ storage-consumer ] ──► TimescaleDB(tag_samples)
                                                                       │
                                                                       ├──► [ anomaly-detector ]
                                                                       │     fits 3-detector ensemble
                                                                       │     scores sliding 60s windows
                                                                       │     writes tag_anomalies
                                                                       │     persists ensemble.joblib ─┐
                                                                       │                              │
                                                                       ▼                              ▼
                                                                  [ inference (FastAPI) ]  ◄─────────┘
                                                                  /forecast  /anomaly  /explain
                                                                       ▲
                                                                       │
                                                                  [ Grafana ]  ──── reads from Timescale
```

See [`docs/architecture.md`](docs/architecture.md) for the live-vs-stubbed
breakdown and the M3 / M4 components that aren't yet wired in.

---

## Repo layout — and where everything is documented

Every component has its own README. The links below point to it; click
through for endpoints, env vars, and how-to-run/test.

### Top-level

| File | Purpose |
|---|---|
| [`SPEC.md`](SPEC.md) | **Canonical project specification.** Source of truth for scope, stack, milestones, and definition of done. |
| [`CLAUDE.md`](CLAUDE.md) | Working conventions (Python style, OpenSpec workflow, security rules). Derived from `SPEC.md` section 7. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to propose changes, code style, PR requirements. |
| [`docker-compose.yml`](docker-compose.yml) | Local dev stack (`core` + `eval` profiles). |
| [`Makefile`](Makefile) | `make up / down / logs / test / eval / fmt / lint`. |
| [`.env.example`](.env.example) | Template — copy to `.env` and edit. Covers ingest, storage, inference, anomaly. |

### Libraries (`libs/`)

| Lib | What it does |
|---|---|
| [`libs/ingest`](libs/ingest/README.md) | `TagSample` schema, `SyntheticTEP` generator, structlog setup. The wire and simulator layer. |
| [`libs/storage`](libs/storage/README.md) | Timescale schema (`tag_samples`, `tag_anomalies`), idempotent migrator, asyncpg query helpers (`latest_value`, `range_query`, `pivot`). |
| [`libs/forecasting`](libs/forecasting/README.md) | `LightGBMForecaster` + `PatchTSTForecaster` + `EnsembleForecaster`, feature engineering, training CLI. |
| [`libs/anomaly`](libs/anomaly/README.md) | PyOD-backed Isolation Forest + Mahalanobis + EWMA detectors, ensemble scorer, SHAP explainer. |

### Services (`services/`)

| Service | What it does |
|---|---|
| [`services/ingest`](services/ingest/README.md) | Drives the synthetic generator at `REPLAY_HZ`, publishes to `plant.tags`. |
| [`services/storage-consumer`](services/storage-consumer/README.md) | Consumes `plant.tags`, validates, batched `COPY` into `tag_samples`. At-least-once. |
| [`services/anomaly-detector`](services/anomaly-detector/README.md) | Streaming AD worker. Fits ensemble on baseline, scores 60-s windows every 5 s. |
| [`services/inference`](services/inference/README.md) | FastAPI app: `/healthz`, `/readyz`, `/forecast`, `/anomaly`, `/explain`. |

### Eval harnesses (`eval/`)

| Harness | What it does |
|---|---|
| [`eval/forecast_harness.py`](eval/forecast_harness.py) | Backtest naive / LGBM / PatchTST / ensemble × MAE / RMSE / SMAPE on a held-out synthetic TEP slice. |
| [`eval/anomaly_harness.py`](eval/anomaly_harness.py) | Six TEP-style fault scenarios, sliding-window scoring, threshold sweep, best-F1 per scenario. |

### Documentation (`docs/`)

| Doc | What it covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Live-vs-stubbed component map, design decisions, what's deferred per milestone. |
| [`docs/benchmarks.md`](docs/benchmarks.md) | Forecasting + AD benchmark numbers, refreshed by the harnesses. |
| [`docs/deployment.md`](docs/deployment.md) | Local docker compose, k3d / Helm path, air-gapped operation. |

### OpenSpec (`openspec/changes/`)

The project is built spec-first — every component started life as a change
proposal under [`openspec/changes/`](openspec/changes/). Proposals contain
`proposal.md` (why + what), `design.md` (decisions + risks), `tasks.md`
(implementation plan), and a `specs/<capability>/spec.md` delta.

| Change | Status | Capability |
|---|---|---|
| [`add-ingest-pipeline`](openspec/changes/add-ingest-pipeline/) | shipped | `ingest-pipeline` |
| [`add-timescale-storage`](openspec/changes/add-timescale-storage/) | shipped | `timescale-storage` |
| [`add-forecasting-service`](openspec/changes/add-forecasting-service/) | shipped (LGBM half) | `forecasting-service` |
| [`add-patchtst-ensemble`](openspec/changes/add-patchtst-ensemble/) | shipped | modifies `forecasting-service` |
| [`add-anomaly-detection`](openspec/changes/add-anomaly-detection/) | shipped (sans AutoEncoder) | `anomaly-detection` |
| [`add-rag-pipeline`](openspec/changes/archive/2026-05-01-add-rag-pipeline/) | shipped (archived) | `rag-pipeline` (M3) |
| [`add-agent-system`](openspec/changes/archive/2026-05-17-add-agent-system/) | shipped (archived) | `agent-system` (M3) |
| [`add-frontend-dashboard`](openspec/changes/add-frontend-dashboard/) | proposed | `frontend-dashboard` (post-v0.1) |
| [`add-ops-stack`](openspec/changes/add-ops-stack/) | shipped (M4 — this change) | `ops-stack` (M4) |

---

## Conventions in one paragraph

Python 3.11, managed by `uv` (workspace mode; per-package `pyproject.toml`
under `libs/*` and `services/*`). Black + Ruff + mypy strict on new code.
`structlog` JSON output everywhere — no `print()` in production paths.
Config exclusively via `pydantic-settings` `BaseSettings`; `.env` is
gitignored, `.env.example` is committed. Conventional Commits, one branch
per OpenSpec change (`change/<slug>`), no merge without tests + green CI.
Air-gap and zero-paid-services are non-negotiable — defaults run with
`OFFLINE_MODE=1` and `LLM_BACKEND=ollama`. The full set of rules lives in
[`CLAUDE.md`](CLAUDE.md).

---

## Tech stack

Locked choices (see [`SPEC.md`](SPEC.md) section 5; do not propose alternatives
without an OpenSpec change):

| Layer | Choice |
|---|---|
| Streaming | Redpanda (Kafka API) |
| TS database | TimescaleDB (Postgres extension) |
| Forecasting | LightGBM + Nixtla `neuralforecast` (PatchTST) |
| Anomaly | PyOD (Isolation Forest, MCD-Mahalanobis) + custom EWMA + SHAP |
| Async / API | FastAPI + uvicorn |
| Embeddings (M3) | BGE-base / BGE-M3 |
| Vector DB (M3) | Qdrant |
| Graph / memory (M3) | Neo4j Community + Graphiti |
| Agent orchestration (M3) | LangGraph |
| LLM backend | Ollama (default; air-gapped) |
| Drift (M4) | Evidently AI |
| Eval | RAGAS (M3) + custom harnesses (here today) |
| Tracking (M4) | MLflow |
| K8s (M4) | k3s via k3d, packaged with Helm 3 |
| CI / CD (M4) | GitHub Actions, GHCR |

---

## Roadmap

| Milestone | What | Status |
|---|---|---|
| **M1** | docker compose stack + ingest → storage → /forecast + eval | **shipped** |
| **M2** | Anomaly detection ensemble + SHAP + AD eval harness | **shipped (sans AutoEncoder; follow-up)** |
| **M3** | RAG (Qdrant + reranker) + LangGraph agent + Graphiti memory | **shipped** |
| **M4** | Helm chart + drift monitoring + MLflow + CI/CD + final polish | **shipped** |

M4 completes the v0.1 scope. The benchmarks block in
[`docs/benchmarks.md`](docs/benchmarks.md) is refreshed by the nightly
eval job. A recorded walk-through demo is tracked as a post-v0.1
follow-up (it needs a human in front of the stack — not something CI
can produce).

---

## License

Apache 2.0 — see [`LICENSE`](LICENSE).
