# services/storage-consumer

Consumes `plant.tags` from Redpanda, validates each `TagSample`, and writes
batched rows into the `tag_samples` hypertable on TimescaleDB.

## Behaviour

- Manual offset commit only after a successful `COPY`. Ensures at-least-once.
- `BATCH_SIZE` rows or `BATCH_MAX_WAIT_MS` of latency, whichever comes first.
- Invalid payloads (NaN/Inf/missing fields) are logged and skipped, not retried.
- Schema is created/upgraded by the `migrator` one-shot service before this
  one starts (compose `depends_on: condition: service_completed_successfully`).

## Env vars

| Var | Default |
|---|---|
| `KAFKA_BOOTSTRAP` | `redpanda:9092` |
| `KAFKA_TOPIC_PLANT_TAGS` | `plant.tags` |
| `KAFKA_GROUP_ID` | `noether-storage-consumer` |
| `BATCH_SIZE` | `500` |
| `BATCH_MAX_WAIT_MS` | `1000` |
| `POSTGRES_HOST` | `timescaledb` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_DB` | `noether` |
| `POSTGRES_USER` | `noether` |
| `POSTGRES_PASSWORD` | `noether` |

## Run

```
docker compose --profile core up -d storage-consumer
docker compose logs -f storage-consumer
psql -h localhost -U noether -d noether -c \
  "SELECT count(*), max(ts) FROM tag_samples;"
```
