## ADDED Requirements

### Requirement: Continuous tag stream
The ingest service SHALL publish simulated plant tag samples to the
`plant.tags` Kafka topic on Redpanda at a configurable rate, defaulting to
1 Hz across approximately 50 tags drawn from the Tennessee Eastman Process
simulator.

#### Scenario: Default replay produces 1 Hz traffic
- **WHEN** the ingest service starts with default configuration
- **THEN** within 5 seconds it begins publishing to `plant.tags`
- **AND** the per-tag publish rate, measured over a 60-second window,
  equals 1 Hz +/- 5%

#### Scenario: Replay rate is configurable
- **WHEN** the ingest service starts with `REPLAY_HZ=10`
- **THEN** the per-tag publish rate, measured over a 60-second window,
  equals 10 Hz +/- 5%

### Requirement: Schema-validated messages
Every message published to `plant.tags` SHALL conform to the `TagSample`
Pydantic model with fields `tag` (string), `value` (float), `quality`
(integer 0-3), and `ts` (ISO-8601 UTC timestamp). Messages that fail
validation SHALL NOT be published; failures SHALL be logged via structlog.

#### Scenario: Valid sample is published
- **WHEN** the simulator emits a TEP tick for tag `XMEAS_1`
- **THEN** a JSON message matching the `TagSample` schema is produced to
  `plant.tags` keyed by the tag name

#### Scenario: Invalid sample is rejected
- **WHEN** the simulator returns a `NaN` value for any tag
- **THEN** the sample is dropped before publish
- **AND** a structlog event with level `warning` and key
  `event=tagsample_invalid` is emitted

### Requirement: Deterministic and reproducible runs
The ingest service SHALL produce byte-identical message values for the first 600 published messages per tag across consecutive runs given identical `SIM_SEED`, `FAULT_PROFILE`, `FAULT_START_S`, and `REPLAY_HZ` configuration.

#### Scenario: Reproducible default run
- **WHEN** two ingest containers run with identical default configuration
  and `SIM_SEED=42`
- **THEN** the SHA-256 of the first 600 `XMEAS_1` value-payloads matches
  across both runs

### Requirement: Fault injection for evaluation
The ingest service SHALL support injecting any of the 20 standard TEP
fault profiles at a configurable start time, so the same service can drive
the anomaly-detection evaluation harness.

#### Scenario: Fault 4 activates at minute 5
- **WHEN** the ingest service starts with `FAULT_PROFILE=4` and
  `FAULT_START_S=300`
- **THEN** for the first 300 seconds the stream matches a no-fault baseline
- **AND** from t=300s onward the stream reflects the TEP fault-4 profile

### Requirement: Air-gapped operation
The ingest service SHALL operate without any outbound network calls beyond
the Redpanda broker. With `OFFLINE_MODE=1` set, the service SHALL fail
fast at startup if any code path would attempt an external DNS lookup.

#### Scenario: Air-gapped startup
- **WHEN** the ingest service starts with `OFFLINE_MODE=1` in an environment
  where all external DNS is blocked
- **THEN** the service reaches steady-state publishing within 30 seconds
- **AND** no DNS lookups other than the configured Redpanda host are made
