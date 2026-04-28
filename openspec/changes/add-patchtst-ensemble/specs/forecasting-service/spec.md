## MODIFIED Requirements

### Requirement: LightGBM + PatchTST ensemble
The forecasting library SHALL train and serve at least two models per tag
(LightGBM and PatchTST via `neuralforecast`) and an ensemble that combines
them with weights fitted on a held-out validation fold.

#### Scenario: Both models trained
- **WHEN** `python -m noether_forecasting.training --tag XMEAS_7 --model ensemble`
  runs against the synthetic TEP panel
- **THEN** three artefacts are produced under `MODEL_DIR`:
  `xmeas_7.lgbm`, `xmeas_7.patchtst`, `xmeas_7.ensemble`
- **AND** the ensemble artefact carries `weight_lgbm` and `weight_patchtst`
  with `weight_lgbm + weight_patchtst == 1` and both in `[0, 1]`

#### Scenario: Ensemble preferred at serve time
- **WHEN** `MODEL_DIR` contains `xmeas_7.{lgbm,patchtst,ensemble}` and a
  client posts `{"tag": "XMEAS_7", ...}` to `/forecast`
- **THEN** the response `model_version` reflects the ensemble artefact

### Requirement: Eval harness publishes benchmarks
`eval/forecast_harness.py` SHALL backtest naive (last-value), LightGBM,
PatchTST, and the ensemble on at least 3 plant tags and write
per-(model, tag) MAE, RMSE, and SMAPE to `eval/results/forecast.json`.
The harness SHALL fail with non-zero exit code if any tag lacks results
for any of the four models.

#### Scenario: Harness produces benchmark file
- **WHEN** `python -m eval.forecast_harness --tags XMEAS_1 XMEAS_7 XMEAS_13`
  runs against the synthetic TEP panel
- **THEN** `eval/results/forecast.json` is written
- **AND** it contains entries for each of the 4 models × 3 tags
- **AND** each entry has numeric `mae`, `rmse`, and `smape` fields

#### Scenario: Smoke skip
- **WHEN** the harness runs with `--skip patchtst`
- **THEN** the harness exits 0 with naive + LGBM columns only
- **AND** `eval/results/forecast.json` records `model_skipped: ["patchtst","ensemble"]`
