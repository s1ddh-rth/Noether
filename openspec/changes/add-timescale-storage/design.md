## Context

The storage layer is read by every downstream component: forecasting
training, anomaly detection backfills, the agent's SQL tool, Grafana
dashboards. A wrong schema choice here ripples through everything.

The expected scale at v0.1 is small (~50 tags × 1 Hz = ~4.3M rows/day). A
single TimescaleDB instance handles this trivially; no need for distributed
hypertables or multi-node setups.

## Goals / Non-Goals

**Goals:**
- One narrow hypertable, one connection, one Python query layer.
- Bulk insert from the Kafka consumer (>= 5k rows/s sustained even though
  v0.1 throughput is far lower) — gives headroom for backfills.
- Compression policy reduces disk after 7 days.
- Retention policy drops after 90 days in dev (env-overridable).
- Typed query helpers for the most common access patterns: latest value
  per tag, range query per tag, multi-tag pivot.

**Non-Goals (per SPEC §9):**
- Multi-tenant schemas / row-level security.
- Cross-region replication.
- Custom physics-informed transformations stored at the DB layer.

## Decisions

- **Schema:** narrow `tag_samples (ts TIMESTAMPTZ, tag TEXT, value DOUBLE
  PRECISION, quality SMALLINT)`. Hypertable on `ts` with chunk interval of
  1 day. Index on `(tag, ts DESC)`.
- **Compression:** Timescale native compression after 7 days, segmentby
  `tag`, orderby `ts DESC`.
- **Retention:** `drop_chunks` after 90 days (env: `RETENTION_DAYS`).
- **Driver:** `asyncpg` for the consumer (raw COPY for bulk inserts);
  SQLAlchemy 2.x async with asyncpg for the query layer.
- **Migrations:** Alembic, even though there's only one table at v0.1 —
  cheaper to bring it in now than retrofit later.
- **Consumer:** dedicated `services/storage-consumer/` service. Keeping it
  separate from `ingest` means the simulator can be scaled or restarted
  independently from the persistence layer.

## Risks / Trade-offs

- **Wide-vs-narrow schema:** narrow is universally accepted for
  high-cardinality tag stores; the trade-off is more rows but trivial
  schema evolution. Acceptable.
- **Hypertable chunking:** 1 day at 4.3M rows/day = comfortable chunk size.
  If we pivot to higher-frequency tags later we'll revisit; flagged in the
  service README.
- **Consumer back-pressure:** if Timescale slows down, the consumer falls
  behind on Kafka. We accept lag at v0.1 (no SLA); structured logs and a
  Prometheus lag gauge make it visible. SPEC §11 risk: scope creep — we
  resist adding a dead-letter queue at v0.1.
