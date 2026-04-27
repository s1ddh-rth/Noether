## 1. Scaffolding

- [ ] 1.1 Create `services/storage-consumer/` with `pyproject.toml`,
      `Dockerfile`, entrypoint, and `README.md`
- [ ] 1.2 Create `libs/storage/` with `pyproject.toml` and `README.md`
- [ ] 1.3 Pin `asyncpg`, `sqlalchemy[asyncio]>=2`, `alembic` in workspace

## 2. Database

- [ ] 2.1 Add TimescaleDB image to `docker-compose.yml` with healthcheck
- [ ] 2.2 Initial Alembic migration: `tag_samples` table + hypertable
      conversion + index
- [ ] 2.3 Compression policy (segmentby `tag`, after 7 days)
- [ ] 2.4 Retention policy (`drop_chunks`, `RETENTION_DAYS` default 90)

## 3. Consumer service

- [ ] 3.1 aiokafka consumer subscribed to `plant.tags`
- [ ] 3.2 Validate against `TagSample`, drop+log invalid
- [ ] 3.3 Bulk insert via `asyncpg` `copy_records_to_table`, batch size 500
- [ ] 3.4 Commit Kafka offsets only after successful insert

## 4. Query layer

- [ ] 4.1 `latest_value(tag)` → `TagSample`
- [ ] 4.2 `range(tag, start, end)` → `list[TagSample]`
- [ ] 4.3 `pivot(tags, start, end)` → `pandas.DataFrame`
- [ ] 4.4 Connection pool managed via SQLAlchemy async engine

## 5. Observability

- [ ] 5.1 structlog JSON output with `service=storage-consumer` keys
- [ ] 5.2 Prometheus counter `storage_rows_inserted_total`
- [ ] 5.3 Prometheus gauge `storage_consumer_lag_messages`
- [ ] 5.4 Prometheus histogram `storage_insert_batch_latency_ms`

## 6. Tests

- [ ] 6.1 Unit: query helpers against a Testcontainers TimescaleDB
- [ ] 6.2 Integration: end-to-end ingest → consumer → range query, p99 < 5s
- [ ] 6.3 Migration: clean up + reapply leaves identical schema
- [ ] 6.4 Coverage >=70% on `services/storage-consumer/` and `libs/storage/`

## 7. Air-gap

- [ ] 7.1 Verify no outbound DNS beyond broker + Postgres with
      `OFFLINE_MODE=1`

## 8. Docs

- [ ] 8.1 `services/storage-consumer/README.md`: env vars, run, test
- [ ] 8.2 `libs/storage/README.md`: query API, examples
- [ ] 8.3 Storage section added to `docs/architecture.md`
