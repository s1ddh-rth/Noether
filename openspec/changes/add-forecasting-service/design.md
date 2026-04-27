## Context

TEP variables are autocorrelated, multivariate, and slow-varying. Two
families of model cover this well: gradient-boosted trees on engineered
lag/rolling features (LightGBM) and patch-based transformers (PatchTST
via Nixtla). SPEC §5 locks both libraries; this change wires them up
without inventing new algorithms.

The first slice (Milestone 1) only needs the LightGBM baseline serving
behind FastAPI. The PatchTST half can land in the same change but its
quality is a Milestone-3 concern. The eval harness must work end-to-end
from day one because SPEC §10 requires published numbers in
`docs/benchmarks.md`.

## Goals / Non-Goals

**Goals:**
- One `Forecaster` interface with two implementations and an ensemble
  wrapper; identical signatures so the API doesn't change when we swap.
- Reproducible training runs tracked in MLflow.
- Offline eval harness producing MAE / RMSE / SMAPE per variable, written
  to `eval/results/forecast.json` and rendered into `docs/benchmarks.md`.
- p95 inference latency on `/forecast` under 500 ms for one variable, 30
  steps ahead, on a laptop CPU.

**Non-Goals (per SPEC §9):**
- Custom PINNs or hand-written deep models.
- Fine-tuning a foundation model.
- Online / continual learning.
- Real OPC UA streams (we forecast off the simulated TEP store).

## Decisions

- **Service structure:** `services/inference/` is a single FastAPI app
  shared with anomaly detection (one Docker image, one process). The app
  is composed from per-endpoint routers from day one — no `main.py`
  monolith to refactor later. Layout:
    ```
    services/inference/
    ├── app.py              # FastAPI() + include_router(...)
    ├── routers/
    │   ├── __init__.py
    │   ├── forecast.py     # POST /forecast            (this change)
    │   ├── anomaly.py      # POST /anomaly             (anomaly change)
    │   └── explain.py      # POST /explain             (anomaly change)
    ├── deps.py             # shared dependencies (settings, model cache)
    └── health.py           # /health and /metrics
    ```
  This change ships `app.py`, `deps.py`, `health.py`, and
  `routers/forecast.py`. The anomaly change adds the other two routers
  without touching `app.py` beyond a single `include_router` line.
- **Models:** LightGBM (lag features, rolling stats), PatchTST via
  `neuralforecast.NeuralForecast`. Ensemble = simple weighted average
  with weights fitted on a validation fold; do not invent stacking
  beyond what `neuralforecast` and `lightgbm` give us.
- **Forecast horizon:** 30 minutes. With 1 Hz tags this is 1800 steps
  raw — we resample to 1-minute means before forecasting (30 steps).
- **Targets:** at least 3 TEP variables (SPEC §10). Default config
  selects `XMEAS_7`, `XMEAS_9`, `XMEAS_11`.
- **Endpoint:** `POST /forecast` body `{ "tag": str, "horizon_min": int }`,
  returns `{ "tag": str, "ts": [iso...], "yhat": [float...], "lo":
  [float...], "hi": [float...], "model_version": str }`.
- **Versioning:** MLflow model registry. Inference loads the
  `Production`-tagged version on startup.
- **Eval harness:** runs as a one-shot script + a CI job. Splits TEP
  trace by time, evaluates each model and the ensemble, emits the JSON.

## Risks / Trade-offs

- PatchTST training time on CPU is non-trivial. Mitigation: keep the
  default training set small and document a GPU path. Acceptable for v0.1.
- Two model families means two deserialisation paths. We accept the
  complexity because the spec named both libraries.
- SPEC §11 risk: scope creep. We resist adding probabilistic outputs
  beyond the simple ensemble residual quantiles at v0.1.
