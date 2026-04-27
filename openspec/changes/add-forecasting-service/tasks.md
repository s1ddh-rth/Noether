## 1. Scaffolding

- [ ] 1.1 Create `libs/forecasting/` with `pyproject.toml` and `README.md`
- [ ] 1.2 Create `services/inference/` with `pyproject.toml`, `Dockerfile`,
      `app.py`, `deps.py`, `health.py`, `routers/__init__.py`, and
      `README.md`. `app.py` uses `include_router(...)` from day one (no
      monolithic main file to refactor later)
- [ ] 1.3 Pin `lightgbm`, `neuralforecast`, `mlflow`, `pyarrow` in workspace

## 2. Feature engineering

- [ ] 2.1 Resampler: 1 Hz → 1-minute mean, gap-fill via forward-fill
- [ ] 2.2 Lag/rolling feature builder for LightGBM
- [ ] 2.3 Train/val/test time-based split utility

## 3. Models

- [ ] 3.1 LightGBM `Forecaster` implementation
- [ ] 3.2 PatchTST `Forecaster` implementation via `neuralforecast`
- [ ] 3.3 Ensemble wrapper with validation-fold weight fitting
- [ ] 3.4 Common `Forecaster` Protocol in `libs/forecasting/protocol.py`

## 4. Training pipeline

- [ ] 4.1 `train.py` CLI entrypoint per model with `--tag`, `--horizon`
- [ ] 4.2 MLflow tracking: params, metrics, artefacts
- [ ] 4.3 Model registry tag flow: register, promote to `Production`

## 5. Inference service

- [ ] 5.1 `routers/forecast.py` exposes `POST /forecast` matching the
      spec contract; mounted in `app.py` via `include_router`
- [ ] 5.2 Lazy-load `Production` models at startup; cache in memory
- [ ] 5.3 Pydantic request/response models with strict validation
- [ ] 5.4 `request_id`, `latency_ms`, `status` on every log line

## 6. Eval harness

- [ ] 6.1 `eval/forecast_harness.py` runs naive / LightGBM / PatchTST /
      ensemble across configurable tag list
- [ ] 6.2 Writes `eval/results/forecast.json`
- [ ] 6.3 Renders Markdown table into `docs/benchmarks.md`

## 7. Observability

- [ ] 7.1 Prometheus histogram `forecast_inference_latency_ms{tag}`
- [ ] 7.2 Counter `forecast_requests_total{tag,status}`
- [ ] 7.3 Counter `forecast_model_loaded_total{model_version}`

## 8. Tests

- [ ] 8.1 Unit: `Forecaster` Protocol contract for both implementations
- [ ] 8.2 Unit: ensemble produces interval that contains point forecast
- [ ] 8.3 API: 400 on unknown tag, 200 on known tag, response shape
- [ ] 8.4 Latency: 100-call p95 under 500 ms (CI runs against a fixed CPU
      runner; document tolerance band)
- [ ] 8.5 Coverage >=70% on `libs/forecasting/` and `services/inference/`

## 9. Air-gap

- [ ] 9.1 No model-hub downloads at runtime; all artefacts loaded from
      local MLflow tracking dir or mounted volume
- [ ] 9.2 With `OFFLINE_MODE=1`, fail fast on any non-allowlisted DNS

## 10. Eval / Benchmarks

- [ ] 10.1 First benchmark numbers committed to `docs/benchmarks.md`
- [ ] 10.2 CI job re-runs harness on every PR touching `libs/forecasting/`

## 11. Docs

- [ ] 11.1 `services/inference/README.md` covers `/forecast` only at this
      stage (other endpoints land in subsequent changes)
- [ ] 11.2 `libs/forecasting/README.md` shows train + register + serve
- [ ] 11.3 Forecast section added to `docs/architecture.md`
