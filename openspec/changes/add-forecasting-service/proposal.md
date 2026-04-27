## Why

Forecasting is one of the four headline capabilities of Noether
(SPEC §3 (3)). It is the second deliverable inside Milestone 1
(SPEC §8): a baseline LightGBM `/forecast` endpoint with an MAE/RMSE eval
harness against TEP data. Milestone 3 will round it out with the PatchTST
ensemble.

This change introduces the forecasting library, the `/forecast` endpoint
of the inference service, and the offline eval harness — all named in
SPEC §4 (component 3) and SPEC §10 (definition of done).

## What Changes

- Add `libs/forecasting/` with: feature builder, LightGBM training
  pipeline, Nixtla `neuralforecast` PatchTST training pipeline, and an
  ensemble that averages or stacks the two.
- Add `services/inference/` (initial slice) with FastAPI `/forecast`
  endpoint that returns 30-min-ahead forecasts for a configurable list of
  TEP variables (default: at least 3 per SPEC §10).
- Add `eval/forecast_harness.py` that backtests against held-out TEP data
  and writes MAE/RMSE per variable to a results JSON consumed by
  `docs/benchmarks.md`.
- Add MLflow tracking around training runs (model registry plus metrics).

## Capabilities

### New Capabilities
- `forecasting-service`: Train, version, serve, and evaluate 30-min-ahead
  forecasts for plant tags using a LightGBM + PatchTST ensemble.

### Modified Capabilities
_None._

## Impact

- New code: `libs/forecasting/`, `services/inference/` (forecast slice),
  `eval/forecast_harness.py`.
- New deps (justified): `lightgbm` (SPEC §5), `neuralforecast` (SPEC §5
  for PatchTST), `mlflow` (SPEC §5), `pyarrow` (efficient feature dataset
  storage). DataFrames via pandas (already implied).
- Reads from the storage layer added in `add-timescale-storage`
  (depends on it).
- Consumed by: agent system Forecast Agent (`add-agent-system`), frontend
  forecast view (`add-frontend-dashboard`).
- Out of scope: PINNs, fine-tuned domain models (SPEC §9). Online
  learning / continual training (v0.2).
