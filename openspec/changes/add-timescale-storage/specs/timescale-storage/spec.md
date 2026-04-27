## ADDED Requirements

### Requirement: Hypertable schema for tag samples
The system SHALL store plant tag samples in a TimescaleDB hypertable named
`tag_samples` with columns `ts` (TIMESTAMPTZ NOT NULL), `tag` (TEXT NOT
NULL), `value` (DOUBLE PRECISION NOT NULL), and `quality` (SMALLINT NOT
NULL), partitioned on `ts` with a 1-day chunk interval and indexed on
`(tag, ts DESC)`.

#### Scenario: Hypertable exists after migration
- **WHEN** Alembic migrations have been applied against an empty database
- **THEN** `SELECT hypertable_name FROM timescaledb_information.hypertables`
  returns `tag_samples`
- **AND** the index `tag_samples_tag_ts_idx` exists

### Requirement: Streaming consumer persists tags
A Kafka consumer SHALL subscribe to `plant.tags`, validate each message
against the `TagSample` schema, and persist accepted samples to
`tag_samples` using bulk inserts. End-to-end lag (Kafka publish to row
visibility in `tag_samples`) SHALL be under 5 seconds at p99 under default
v0.1 load (50 tags at 1 Hz).

#### Scenario: Round-trip from publish to query
- **WHEN** the ingest service publishes a `TagSample` for `XMEAS_1` at time T
- **THEN** within 5 seconds a `SELECT value FROM tag_samples WHERE tag =
  'XMEAS_1' AND ts >= T - interval '1 second'` returns that value

### Requirement: Compression and retention policies
The hypertable SHALL be compressed after 7 days (`segmentby tag, orderby
ts DESC`) and pruned by `drop_chunks` after `RETENTION_DAYS` (default 90).

#### Scenario: Old chunks compressed
- **WHEN** chunks older than 7 days exist
- **THEN** the periodic compression job marks them as compressed within
  one job interval

#### Scenario: Retention enforced
- **WHEN** `RETENTION_DAYS=30` and chunks older than 30 days exist
- **THEN** the periodic retention job drops them within one job interval

### Requirement: Typed Python query layer
The `libs/storage` package SHALL expose async functions for: latest value
per tag, range query for a single tag over a time window, and pivot query
returning a wide DataFrame for a list of tags over a time window. All
return types SHALL be Pydantic models or pandas DataFrames with typed
columns.

#### Scenario: Latest value query
- **WHEN** `await storage.latest_value("XMEAS_1")` is called
- **THEN** the return is a `TagSample` matching the most recent row for
  that tag

#### Scenario: Range query
- **WHEN** `await storage.range("XMEAS_1", start, end)` is called with a
  one-hour window
- **THEN** the return is a list of `TagSample` ordered by `ts` ascending

### Requirement: Air-gapped operation
The storage consumer SHALL operate without any outbound network calls
beyond the Redpanda broker and the TimescaleDB instance. With
`OFFLINE_MODE=1` set, the service SHALL fail fast at startup if any code
path would attempt an external DNS lookup.

#### Scenario: Air-gapped startup
- **WHEN** the storage consumer starts with `OFFLINE_MODE=1` in an
  environment where all external DNS is blocked
- **THEN** the service reaches steady-state consumption within 30 seconds
- **AND** no DNS lookups other than the configured Redpanda and Postgres
  hosts are made
