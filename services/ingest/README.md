# services/ingest

pyTEP-style replayer that publishes plant tag samples to Redpanda.

## What it does

- Runs a `SyntheticTEP` generator producing 52 tags (`XMEAS_1..41`, `XMV_1..11`) per tick.
- Validates each sample against `TagSample` (Pydantic) and drops/logs anything non-finite.
- Publishes to topic `plant.tags`, keyed by tag name, lz4-compressed, idempotent producer.
- Rate-limited to `REPLAY_HZ` (default 1 Hz) using a monotonic deadline.

## Env vars

| Var | Default | Notes |
|---|---|---|
| `KAFKA_BOOTSTRAP` | `redpanda:9092` | Broker(s), comma-separated. |
| `KAFKA_TOPIC_PLANT_TAGS` | `plant.tags` | Wire topic. |
| `REPLAY_HZ` | `1.0` | Ticks per second. |
| `SIM_SEED` | `42` | Generator seed; identical seeds → identical streams. |
| `FAULT_PROFILE` | `none` | `none` / `step` / `drift` / `spike`. |
| `FAULT_START_S` | `0` | Seconds from start before fault is applied. |
| `OFFLINE_MODE` | `1` | Set to `0` to allow non-broker DNS. |
| `LOG_LEVEL` | `info` | structlog level. |

## Run

```
docker compose --profile core up -d ingest
docker compose logs -f ingest
```

## Test

```
uv run pytest libs/ingest
```

## Air-gap

Default config makes no DNS lookups beyond the Kafka broker. There are no
external HTTP clients or model downloads on the hot path.
