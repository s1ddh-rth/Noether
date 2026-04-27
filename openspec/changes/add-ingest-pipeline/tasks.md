## 1. Scaffolding

- [ ] 1.1 Create `services/ingest/` with `pyproject.toml`, `Dockerfile`, and entrypoint
- [ ] 1.2 Add `services/ingest/README.md` covering purpose, env vars, run, test
- [ ] 1.3 Pin `pytep` and `aiokafka` versions in the workspace `pyproject.toml`

## 2. Schema

- [ ] 2.1 Define `TagSample` Pydantic model in `libs/ingest/schema.py`
- [ ] 2.2 Add settings model via `pydantic-settings` (`REPLAY_HZ`, `SIM_SEED`,
      `FAULT_PROFILE`, `FAULT_START_S`, `KAFKA_BOOTSTRAP`, `OFFLINE_MODE`)

## 3. Simulator and publisher

- [ ] 3.1 Wrap pyTEP into a generator that yields tag samples per tick
- [ ] 3.2 Implement async aiokafka producer publishing to `plant.tags`,
      keyed by tag name
- [ ] 3.3 Implement rate-limited tick loop honouring `REPLAY_HZ`
- [ ] 3.4 Implement fault injection via `FAULT_PROFILE` / `FAULT_START_S`
- [ ] 3.5 Drop-and-log invalid samples (NaN, schema violations)

## 4. Infra wiring

- [ ] 4.1 Add Redpanda service to `docker-compose.yml` with healthcheck
- [ ] 4.2 Add ingest service to `docker-compose.yml`, depending on Redpanda
- [ ] 4.3 Create `plant.tags` topic at startup via init container or rpk

## 5. Observability

- [ ] 5.1 structlog JSON output with `service=ingest`, `tag`, `event` keys
- [ ] 5.2 Prometheus counter for `ingest_messages_published_total{tag}`
- [ ] 5.3 Prometheus histogram for `ingest_publish_latency_ms`

## 6. Tests

- [ ] 6.1 Unit: `TagSample` validation (happy path, NaN, missing field)
- [ ] 6.2 Unit: rate limiter holds `REPLAY_HZ` within 5%
- [ ] 6.3 Integration (docker compose): produce 600 messages, assert count and
      schema for each
- [ ] 6.4 Reproducibility: two runs with identical seed produce identical
      payload SHA-256
- [ ] 6.5 Coverage >=70% on new code in `services/ingest/` and `libs/ingest/`

## 7. Air-gap

- [ ] 7.1 With `OFFLINE_MODE=1`, fail fast on any non-broker DNS lookup
- [ ] 7.2 Document air-gapped run in `services/ingest/README.md`

## 8. Docs

- [ ] 8.1 Service-level README updated with all env vars and an example run
- [ ] 8.2 Add ingest section to `docs/architecture.md`
