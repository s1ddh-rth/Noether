## Context

The replayer is the upstream source of truth for the rest of the system in
v0.1. It must be deterministic enough to support reproducible eval (forecast
MAE/RMSE, AD precision/recall) and fast enough that `docker compose up`
brings the full stack online in under 60 seconds (SPEC §10).

Tennessee Eastman is the chosen simulator (SPEC §6). pyTEP gives Python
bindings; there is no need to host the original Fortran binary directly.

## Goals / Non-Goals

**Goals:**
- One process that owns simulation tick + Kafka publish.
- Configurable replay rate (`REPLAY_HZ`, default 1).
- Configurable fault injection so the same service can produce labelled
  faulty traces for the anomaly eval harness.
- Schema-validated messages — every published record passes a Pydantic model
  before hitting the broker.
- Air-gapped: no outbound HTTP at runtime.

**Non-Goals (per SPEC §9):**
- Real OPC UA / SCADA / DCS connectors.
- Multi-tenant or multi-plant simulations.
- Websocket or HTTP push to the frontend (frontend reads from Timescale, not
  Kafka).

## Decisions

- **Simulator:** pyTEP. It's the dataset SPEC §6 locks in and gives a
  deterministic per-tick API.
- **Broker:** Redpanda (SPEC §5). Single broker in dev; Helm chart later
  uses the upstream Redpanda chart.
- **Kafka client:** `aiokafka` for async-native FastAPI compatibility.
  Alternative `confluent-kafka` rejected because it ships a C extension that
  complicates the slim-image build and isn't required at v0.1 throughput.
- **Schema:** JSON over Kafka (not Avro/Protobuf). Pydantic model
  `TagSample { tag: str, value: float, quality: int, ts: datetime }`.
  Avro can be a v0.2 change if a schema registry is wanted.
- **Topic:** single topic `plant.tags`, keyed by tag name (gives natural
  per-tag ordering and partition affinity).
- **Determinism:** seed fed via `SIM_SEED` env var; default fixed for repro.
- **Fault injection:** `FAULT_PROFILE` env var selects a TEP fault number
  (1–20); `FAULT_START_S` controls when it activates relative to start.

## Risks / Trade-offs

- pyTEP's wheel availability across platforms is a known footgun — mitigation:
  document supported platforms in the service README and pin the version in
  `pyproject.toml`. If pyTEP doesn't install cleanly on Windows, the
  `services/ingest/` Dockerfile is the supported runtime, not host Python.
- 1 Hz × 50 tags × 1 byte payload is trivial throughput; the design is
  deliberately oversized to cover later milestones without rework. SPEC §11
  flags scope creep — we resist adding a schema registry now.
- JSON wire format trades efficiency for legibility. Acceptable at v0.1 scale.
