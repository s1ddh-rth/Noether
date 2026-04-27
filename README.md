# Noether

> **Open-source reference architecture for industrial AI copilots.**
> Real-time anomaly detection, forecasting, and natural-language reasoning over
> simulated plant data. Physics-grounded, air-gappable, deployable on a laptop
> or a k3s cluster.

This repo is **work in progress** — see [`SPEC.md`](./SPEC.md) for the full
project specification and [`docs/architecture.md`](./docs/architecture.md) for
the current, live system shape.

## Status — Milestone 1 (Foundation)

What's running today via `docker compose --profile core up`:

- **Redpanda** — Kafka API for the `plant.tags` stream.
- **TimescaleDB** — `tag_samples` hypertable, compression + retention policies.
- **`services/ingest`** — synthetic TEP replayer publishing 52 tags at 1 Hz.
- **`services/storage-consumer`** — Kafka → Timescale, batched COPY, at-least-once.
- **`services/inference`** — FastAPI with `POST /forecast` backed by
  per-tag LightGBM models baked into the image.
- **Grafana** — starter dashboard reading from Timescale.

Run the forecast eval harness end-to-end (M1 deliverable):

```
make eval
```

This prints a Markdown table of MAE/RMSE for the naive baseline vs. LightGBM
and writes `eval/results/forecast.json`.

## Quickstart

```
git clone git@github-personal:s1ddh-rth/Noether.git
cd Noether
cp .env.example .env
make up        # docker compose --profile core up -d
make logs      # tail everything
```

Hit the inference API once the stack is healthy:

```
curl -X POST http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

## Layout

```
SPEC.md                  # canonical spec — source of truth
CLAUDE.md                # working conventions for Claude Code
docker-compose.yml       # M1 dev stack
Makefile                 # make up / down / test / eval / fmt / lint

libs/
  ingest/                # noether-ingest: TagSample, SyntheticTEP, structlog setup
  storage/               # noether-storage: Timescale schema, migrations, query helpers
  forecasting/           # noether-forecasting: LightGBM forecaster + features

services/
  ingest/                # noether-svc-ingest: TEP replayer
  storage-consumer/      # noether-svc-storage-consumer: Kafka → Timescale
  inference/             # noether-svc-inference: FastAPI /forecast

eval/
  forecast_harness.py    # M1 eval harness — naive vs LightGBM

openspec/
  changes/               # 8 OpenSpec change proposals (one per SPEC §4 component)
docs/
  architecture.md
  benchmarks.md
  deployment.md
infra/
  grafana/provisioning/  # datasources + starter dashboards
```

## Roadmap

| Milestone | What | Status |
|---|---|---|
| **M1** | docker compose stack + ingest → storage → /forecast + eval | **in progress** |
| M2 | Anomaly detection ensemble (Isolation Forest + AE + Mahalanobis + EWMA) + SHAP | pending |
| M3 | RAG (Qdrant + reranker) + LangGraph agent + Graphiti memory | pending |
| M4 | Helm chart + drift monitoring + MLflow + CI/CD + final polish | pending |

## License

Apache 2.0. See [LICENSE](./LICENSE).
