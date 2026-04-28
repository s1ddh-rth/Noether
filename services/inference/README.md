# services/inference

FastAPI inference service for forecasting + anomaly scoring + explanation.

## Endpoints

| Path | Auth | Notes |
|---|---|---|
| `GET /healthz` | none | liveness probe |
| `GET /readyz` | none | readiness; lists tags with forecast artefacts |
| `POST /forecast` | `X-API-Key` | horizon-ahead prediction (LGBM / PatchTST / ensemble) |
| `POST /anomaly` | `X-API-Key` | score a tag window with the AD ensemble |
| `POST /explain` | `X-API-Key` | per-tag SHAP-blended contributions for a stored alert |

### `POST /forecast`

```json
{
  "tag": "XMEAS_1",
  "history": [
    { "ts": "2026-01-01T00:00:00Z", "value": 12.34 },
    ...
  ]
}
```

Response:

```json
{
  "request_id": "uuid",
  "tag": "XMEAS_1",
  "horizon_min": 30,
  "point": 13.21,
  "lower": 12.85,
  "upper": 13.57,
  "model_version": "ensemble-v0-seed42-h30",
  "model_kind": "ensemble",
  "latency_ms": 7
}
```

The registry resolves `<MODEL_DIR>/<tag>.{ensemble,patchtst,lgbm}` in priority
order — drop a `.ensemble` artefact and `/forecast` automatically prefers it.
See [`libs/forecasting/README.md`](../../libs/forecasting/README.md) for how
to train each kind.

### `POST /anomaly`

```json
{
  "tags": ["XMEAS_1", "XMEAS_2", ..., "XMV_2"],
  "start": "2026-04-28T10:00:00Z",
  "end":   "2026-04-28T10:01:00Z"
}
```

Response carries the rank-normalised ensemble score, per-detector breakdown,
and the boolean alert flag:

```json
{
  "request_id": "uuid",
  "score": 0.83,
  "detectors": { "iforest": 0.71, "mahalanobis": 0.83, "ewma": 0.42 },
  "tags": ["XMEAS_1", ...],
  "alert": true,
  "latency_ms": 12
}
```

`503` until the [`anomaly-detector` service](../anomaly-detector/README.md)
has fitted a baseline ensemble.

### `POST /explain`

```json
{ "alert_id": "uuid-from-tag_anomalies" }
```

Returns per-tag contributions sorted by magnitude descending, rescaled so
their absolute values sum to the alert score within ±5%. Isolation-Forest
contributions come from `shap.TreeExplainer`; Mahalanobis and EWMA use
analytic per-tag breakdowns. See
[`libs/anomaly/README.md`](../../libs/anomaly/README.md) for details.

## Env vars

| Var | Default |
|---|---|
| `INFERENCE_HOST` | `0.0.0.0` |
| `INFERENCE_PORT` | `8000` |
| `MODEL_DIR` | `/app/models` |
| `INFERENCE_API_KEY` | `changeme-please` |
| `FORECAST_HORIZON_MIN` | `30` |
| `POSTGRES_*` | as elsewhere; required by `/anomaly` and `/explain` |

## Run

```
docker compose --profile core up -d inference
curl -X POST http://localhost:8000/forecast \
  -H "X-API-Key: changeme-please" \
  -H "Content-Type: application/json" \
  -d @sample-request.json
```

## Test

```
uv run pytest services/inference
```
