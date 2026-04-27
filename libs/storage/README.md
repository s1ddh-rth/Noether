# noether-storage

TimescaleDB schema, migrations, and query helpers.

## Schema

One hypertable: `tag_samples (ts timestamptz, tag text, value double, quality text)`.
- `chunk_time_interval = '1 day'`
- Compression after 7 days, segment-by `tag`, order-by `ts DESC`.
- Retention policy drops chunks older than `RETENTION_DAYS` (default 90).
- Index on `(tag, ts DESC)`.

## Migrations

Idempotent runner — no Alembic for v0.1.

```
python -m noether_storage.migrations.run
```

Compose runs this automatically as the `migrator` service before
`storage-consumer` starts.

## Query API

```python
from sqlalchemy.ext.asyncio import create_async_engine
from noether_storage import async_dsn, latest_value, range_query, pivot

engine = create_async_engine(async_dsn())
sample = await latest_value(engine, "XMEAS_1")
window = await range_query(engine, "XMEAS_1", start, end)
df = await pivot(engine, ["XMEAS_1", "XMEAS_7"], start, end)
```
