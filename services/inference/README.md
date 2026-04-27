# services/inference

FastAPI inference service. M1 ships `/forecast` only; `/anomaly` and `/explain`
land in subsequent milestones.

## Endpoints

| Path | Auth | Notes |
|---|---|---|
| `GET /healthz` | none | liveness |
| `GET /readyz` | none | readiness; lists known tags |
| `POST /forecast` | `X-API-Key` | horizon-ahead prediction |

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
  "model_version": "lgbm-v0-seed42-h30",
  "latency_ms": 7
}
```

## Models

The Docker image bakes in baseline forecasters for `XMEAS_1`, `XMEAS_7`,
`XMEAS_13` at build time (`noether_forecasting.training`). Re-train locally
with:

```
python -m noether_forecasting.training --tag XMEAS_5 --output models/xmeas_5.lgbm
```

The service lazy-loads each artifact on first request to that tag and caches
it in process memory.

## Env vars

| Var | Default |
|---|---|
| `INFERENCE_HOST` | `0.0.0.0` |
| `INFERENCE_PORT` | `8000` |
| `MODEL_DIR` | `/app/models` |
| `INFERENCE_API_KEY` | `changeme-please` |
| `FORECAST_HORIZON_MIN` | `30` |

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
