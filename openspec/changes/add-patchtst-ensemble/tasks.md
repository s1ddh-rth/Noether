## 1. Scaffolding

- [ ] 1.1 Create `libs/forecasting/noether_forecasting/protocol.py` with the
      `Forecaster` Protocol and a shared `ForecastResult` model
- [ ] 1.2 Add `neuralforecast`, `torch` (CPU) to `libs/forecasting/pyproject.toml`
- [ ] 1.3 Update inference Dockerfile to apt-install build deps if needed

## 2. PatchTST forecaster

- [ ] 2.1 `libs/forecasting/noether_forecasting/patchtst.py`:
      `PatchTSTForecaster` wrapping `neuralforecast.NeuralForecast`
- [ ] 2.2 fit/predict/save/load conforming to the `Forecaster` Protocol
- [ ] 2.3 Pickle the `NeuralForecast` instance (joblib) plus metadata —
      same artefact pattern as LGBM, `.patchtst` extension

## 3. Ensemble forecaster

- [ ] 3.1 `libs/forecasting/noether_forecasting/ensemble.py`:
      `EnsembleForecaster(lgbm, patchtst)` combining their point forecasts
- [ ] 3.2 `_fit_weights(y_val, y_lgbm_val, y_patchtst_val)` — convex MSE
- [ ] 3.3 Save/load to `.ensemble` (writes member artefact paths inside)

## 4. Training CLI

- [ ] 4.1 Extend `noether_forecasting.training` with `--model {lgbm,patchtst,ensemble}`
- [ ] 4.2 `--max-steps` for PatchTST CPU budget
- [ ] 4.3 Print one JSON line per artefact written (already done for LGBM)

## 5. Inference dispatch

- [ ] 5.1 `services/inference/noether_svc_inference/deps.py` —
      `ModelRegistry.get(tag)` globs for `.ensemble` → `.patchtst` → `.lgbm`
- [ ] 5.2 `routers/forecast.py` calls `model.predict(X)` regardless of kind

## 6. Eval harness

- [ ] 6.1 `eval/forecast_harness.py` adds PatchTST and ensemble columns
- [ ] 6.2 Adds an `smape` field to each result row
- [ ] 6.3 Fails with non-zero exit if any tag is missing any of the four
      model results (matches `forecasting-service` spec scenario)
- [ ] 6.4 `--skip patchtst` flag for smoke runs

## 7. Tests

- [ ] 7.1 Unit: `Forecaster` Protocol contract holds for both classes
- [ ] 7.2 Unit: `EnsembleForecaster` weights sum to 1, both in [0, 1]
- [ ] 7.3 Unit: ensemble interval contains both member point forecasts
- [ ] 7.4 Coverage ≥ 70% on new code in `libs/forecasting/`

## 8. Air-gap

- [ ] 8.1 No model hub downloads at runtime; PatchTST artefacts live
      under `MODEL_DIR`. Verify with `OFFLINE_MODE=1` smoke
- [ ] 8.2 `neuralforecast` does not initiate network access on import

## 9. Eval / Benchmarks

- [ ] 9.1 First multi-model benchmark numbers committed to
      `docs/benchmarks.md`
- [ ] 9.2 Update SPEC section 10 status (forecast benchmark deliverable)

## 10. Docs

- [ ] 10.1 `libs/forecasting/README.md`: train all three, serve all three
- [ ] 10.2 Note PatchTST CPU budget in `docs/architecture.md`
