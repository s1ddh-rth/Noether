# services/anomaly-detector

Streaming anomaly detector. Fits a 3-detector ensemble on a baseline window
of recent clean data, then scores 60-second windows every 5 seconds and
writes results to the `tag_anomalies` Timescale hypertable.

## Behaviour

- On startup, polls `tag_samples` until `ANOMALY_WARMUP_MIN` minutes of
  data are available.
- Fits an `AnomalyEnsemble(IsolationForest + Mahalanobis + EWMA)` on the
  most recent `ANOMALY_BASELINE_MIN` minutes.
- Persists the fitted ensemble to `ANOMALY_ENSEMBLE_PATH` (default
  `/app/models/anomaly_ensemble.joblib`) so the inference service's
  `/anomaly` endpoint can use the same model.
- Loops every `ANOMALY_STRIDE_S` seconds: pivot last `ANOMALY_WINDOW_S`
  seconds, score, insert one row into `tag_anomalies`. Each row carries
  `score`, the per-detector breakdown, the `alert` boolean, and the tag
  set used for scoring.

## Env vars

| Var | Default |
|---|---|
| `ANOMALY_WINDOW_S` | `60` |
| `ANOMALY_STRIDE_S` | `5` |
| `ANOMALY_WARMUP_MIN` | `5` |
| `ANOMALY_BASELINE_MIN` | `30` |
| `ANOMALY_TAGS` | `XMEAS_1..8,XMV_1..2` (10 tags by default) |
| `ANOMALY_THRESHOLD` | `0.95` |
| `ANOMALY_ENSEMBLE_PATH` | `/app/models/anomaly_ensemble.joblib` |
| `MODEL_DIR` | `/app/models` |
| `POSTGRES_*` | as in services/storage-consumer |

## Run

```
docker compose --profile core up -d anomaly-detector
docker compose logs -f anomaly-detector
psql -h localhost -U noether -d noether -c \
  "SELECT ts, score, alert FROM tag_anomalies ORDER BY ts DESC LIMIT 10;"
```

## Why no autoencoder?

PyOD ships a torch-backed AutoEncoder, but PyTorch in the AD service path
adds ~600 MB to the image and ~500 MB of resident memory. The IF +
Mahalanobis + EWMA trio is sufficient for the TEP fault families this
project ships against (mean shift, drift, intermittent spikes). An
autoencoder lands in a follow-up change once the rest of M2 is stable.
