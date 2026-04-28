## Why

Milestone 1 of `add-forecasting-service` shipped the LightGBM half of the
forecasting story. The `forecasting-service` capability spec already requires
a **LightGBM + PatchTST ensemble** (SPEC section 4 component 3 and
SPEC section 5). Without PatchTST and the ensemble, the `/forecast` endpoint
serves only a single tabular model and the eval harness reports only two
columns (naive vs LGBM) instead of the four required by the capability
spec (naive / LGBM / PatchTST / ensemble).

This change closes that gap. It is in scope for v0.1 — SPEC section 10's
"Definition Of Done" requires "MAE table for at least 3 TEP variables vs.
naive/ARIMA/LightGBM/PatchTST published in `docs/benchmarks.md`".

## What Changes

- Add `neuralforecast` (Nixtla) and `torch` (CPU) to `libs/forecasting`.
- Implement `noether_forecasting.patchtst.PatchTSTForecaster` with the same
  `Forecaster` Protocol surface as `LightGBMForecaster` (fit/predict/save/load).
- Implement `noether_forecasting.ensemble.EnsembleForecaster` that combines
  LightGBM and PatchTST point forecasts with weights fitted on a held-out
  validation fold.
- Extend the training CLI to support `--model {lgbm,patchtst,ensemble}` and
  produce one artefact per model per tag.
- Extend `eval/forecast_harness.py` with PatchTST and ensemble columns and
  an SMAPE column to satisfy the existing capability spec scenario.
- Update inference `routers/forecast.py` so the registry can load any of
  the three artefact kinds from `MODEL_DIR` (file extension keyed: `.lgbm`,
  `.patchtst`, `.ensemble`).

## Capabilities

### New Capabilities
_None._

### Modified Capabilities
- `forecasting-service`: PatchTST and the ensemble become part of the
  served model set; the eval harness reports four model columns + SMAPE
  per the existing spec.

## Impact

- Code: `libs/forecasting/noether_forecasting/{patchtst.py,ensemble.py,
  protocol.py}`, `eval/forecast_harness.py` (new columns),
  `services/inference/noether_svc_inference/routers/forecast.py` (loader
  dispatch), `services/inference/Dockerfile` (libgomp + torch).
- New deps (justified): `neuralforecast>=2.0,<3` (the named library in
  SPEC section 5; nothing in the locked stack covers PatchTST), `torch>=2.5,<3`
  (CPU-only wheel; required by `neuralforecast`). Image size grows by
  ~700 MB; we mitigate by training PatchTST in a one-shot job and only
  pulling artefacts at serve time.
- Eval runtime grows. Default `--hours 48` smoke run trains PatchTST in
  ~30 s per tag on CPU; full `--hours 168` runs are jobs, not smoke tests.
- Out of scope: GPU training, mixed-precision, custom architectures
  (SPEC section 9). Online retraining (v0.2).
