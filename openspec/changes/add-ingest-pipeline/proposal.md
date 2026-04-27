## Why

Noether's runtime starts with a continuous stream of plant tag data. Every
downstream component (storage, forecasting, anomaly detection, agents) assumes
this stream exists. Without it, nothing else can be built or evaluated.

This change establishes the head of the data pipeline using the simulated
Tennessee Eastman Process (pyTEP) as the data source — per **SPEC §3 (1)**,
**SPEC §4 (component 1)**, and **SPEC §6 (datasets)**. It is a prerequisite
for **Milestone 1** (SPEC §8).

## What Changes

- Add a `services/ingest/` service that runs the pyTEP simulator and replays
  ~50 plant tags at a configurable rate (default 1 Hz) onto a Redpanda topic.
- Add a `plant.tags` Kafka topic on Redpanda with a single Pydantic-defined
  JSON schema for tag samples (`tag`, `value`, `quality`, `ts`).
- Provide replay-rate control (`REPLAY_HZ`) and fault-injection controls so
  the same simulator can later drive the AD evaluation harness.
- Containerise both the replayer and Redpanda; add to `docker-compose.yml`.

## Capabilities

### New Capabilities
- `ingest-pipeline`: Generate, schema-validate, and publish simulated plant
  tag samples to a Kafka-compatible stream at controllable rates.

### Modified Capabilities
_None — this is the first change for this surface._

## Impact

- New code: `services/ingest/` (Python, FastAPI optional health endpoint),
  `libs/ingest/schema.py` (Pydantic models).
- New infra: Redpanda container in `docker-compose.yml`; topic created at
  service startup or via an init container.
- New deps (require justification per the library-discipline rule):
  `pytep` (TEP simulator — SPEC §6 names it as the primary dataset; no
  in-stack alternative), `confluent-kafka` or `aiokafka` (Kafka client; pick
  one in design.md), `pydantic-settings` (already implied by SPEC §7).
- Documentation: `services/ingest/README.md`.
- Out of scope: real OPC UA/SCADA connectors (SPEC §9).
