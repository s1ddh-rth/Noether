## Why

Tag samples flowing through Redpanda must be persisted to a queryable
time-series store so that the forecasting service can fit models, the agent
SQL tool can answer historical questions, and Grafana can visualise live
behaviour. SPEC §3 (2), SPEC §4 (component 2), and SPEC §5 lock in
TimescaleDB hypertables for this role. This change is a Milestone 1
prerequisite (SPEC §8).

## What Changes

- Provision TimescaleDB in `docker-compose.yml`.
- Define a single hypertable schema for plant tag samples with a compression
  policy (after 7 days) and a retention policy (drop after 90 days in dev,
  longer in prod).
- Add a `services/storage-consumer/` service that consumes `plant.tags` from
  Redpanda and bulk-inserts into TimescaleDB.
- Provide a Python data-access library `libs/storage/` so the inference,
  agent, and eval services share one tested query layer.

## Capabilities

### New Capabilities
- `timescale-storage`: Persist plant tag samples to a TimescaleDB hypertable
  via a streaming Kafka consumer, with compression and retention policies,
  and expose a typed Python query layer.

### Modified Capabilities
_None._

## Impact

- New code: `services/storage-consumer/`, `libs/storage/` (SQLAlchemy +
  asyncpg models, query helpers).
- New infra: TimescaleDB image in `docker-compose.yml`, init SQL for
  hypertable + policies, env-driven connection settings.
- New deps (justified): `asyncpg` (async Postgres driver — necessary for
  bulk inserts at line rate), `sqlalchemy` (typed query layer; SPEC §5
  doesn't lock an ORM but pydantic-settings + sqlalchemy is the boring
  choice), `psycopg[binary]` only if needed for migrations.
- Tooling: `alembic` for migrations.
- Documentation: `services/storage-consumer/README.md`, `libs/storage/README.md`.
- Out of scope: Cross-region replication, multi-tenant schemas (SPEC §9).
