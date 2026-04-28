# Architecture

See **SPEC section 4** for the canonical diagram. This file annotates the pieces
that exist today (M1) and what's stubbed.

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

## Out of M1 (planned)

- PatchTST forecaster + ensemble (M1 follow-up or M2)
- Prometheus exporters in every service (M4)
- MLflow model registry (M4)
- Grafana dashboards beyond the starter `plant-tags` board (M4)
- Real Tennessee Eastman simulator (later, behind a change proposal)
