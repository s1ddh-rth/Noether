## ADDED Requirements

### Requirement: Forecast endpoint
The inference service SHALL expose `POST /forecast` accepting a JSON body
`{ "tag": str, "horizon_min": int }`. It SHALL return a JSON body with
`tag`, `ts` (ISO-8601 list of horizon timestamps), `yhat`, `lo`, `hi`
(equal-length numeric lists representing point and interval forecasts),
and `model_version` (a string identifying the loaded model).

#### Scenario: Valid forecast request
- **WHEN** a client posts `{"tag": "XMEAS_7", "horizon_min": 30}` to
  `/forecast` and trained model artefacts exist
- **THEN** the response status is 200
- **AND** `len(yhat) == len(ts) == len(lo) == len(hi) == 30`
- **AND** `lo[i] <= yhat[i] <= hi[i]` for every `i`

#### Scenario: Unknown tag
- **WHEN** a client posts `{"tag": "UNKNOWN_TAG", "horizon_min": 30}`
- **THEN** the response status is 400
- **AND** the response body contains `{"detail": "...unknown tag..."}`

### Requirement: Inference latency budget
The `/forecast` endpoint SHALL maintain p95 latency under 500 ms for a single tag at horizon 30 minutes, measured over 100 consecutive requests against a warmed service on a single laptop CPU (4 cores, 16 GB RAM).

#### Scenario: Latency under load
- **WHEN** 100 sequential `/forecast` calls are made for `XMEAS_7` at
  horizon 30
- **THEN** the p95 wall-clock latency is under 500 ms

### Requirement: LightGBM + PatchTST ensemble
The forecasting library SHALL train and serve at least two models per tag
(LightGBM and PatchTST) and an ensemble that combines them with weights
fitted on a held-out validation fold.

#### Scenario: Both models trained
- **WHEN** `python -m libs.forecasting.train --tag XMEAS_7` runs against
  TEP data
- **THEN** MLflow records two trained model versions and one ensemble
  configuration for `XMEAS_7`

### Requirement: Eval harness publishes benchmarks
`eval/forecast_harness.py` SHALL backtest naive (last-value), LightGBM,
PatchTST, and the ensemble on at least 3 TEP variables and write
per-(model, variable) MAE, RMSE, and SMAPE to
`eval/results/forecast.json`. The harness SHALL fail with non-zero exit
code if any variable lacks results.

#### Scenario: Harness produces benchmark file
- **WHEN** `python eval/forecast_harness.py --vars XMEAS_7,XMEAS_9,XMEAS_11`
  runs against the TEP test split
- **THEN** `eval/results/forecast.json` is written
- **AND** it contains an entry for each of the 4 models × 3 variables
- **AND** each entry has numeric `mae`, `rmse`, and `smape` fields

### Requirement: Air-gapped operation
Forecast training and inference SHALL operate without any outbound
network calls. With `OFFLINE_MODE=1`, the service SHALL fail fast at
startup if any code path would attempt an external DNS lookup (including
model-hub downloads).

#### Scenario: Air-gapped serve
- **WHEN** the inference service starts with `OFFLINE_MODE=1` and a
  pre-trained model present locally
- **THEN** `/forecast` responds 200 within 30 seconds of container start
- **AND** no DNS lookups other than configured local services occur
