## ADDED Requirements

### Requirement: Streaming AD worker
A worker SHALL consume tag windows from TimescaleDB on a sliding
60-second window with 5-second stride, score them via the ensemble
detector, and persist results to the `tag_anomalies` hypertable. Alerts
above the configured threshold SHALL also be published to a
`plant.anomalies` Kafka topic.

#### Scenario: Score every window
- **WHEN** the worker has been running for 60 seconds against a live
  ingest stream
- **THEN** at least 11 rows exist in `tag_anomalies` for that minute
  (12 windows minus startup) with non-null `score` and per-detector breakdown
  in `detectors`

#### Scenario: Alert publication
- **WHEN** the ensemble score for a window exceeds the configured
  threshold
- **THEN** a JSON message is produced to `plant.anomalies` with the alert
  id, score, top contributing tags, and timestamp

### Requirement: Anomaly endpoint
The inference service SHALL expose `POST /anomaly` accepting `{ "tags":
[str], "start": iso8601, "end": iso8601 }` and returning
`{ "score": float, "detectors": { "iforest": float, "autoencoder": float,
"mahalanobis": float, "ewma": float }, "tags": [str], "alert": bool }`.

#### Scenario: Score a quiet window
- **WHEN** a client requests `/anomaly` for the default tag set over a
  no-fault baseline window
- **THEN** the response status is 200
- **AND** `alert == false`
- **AND** `0.0 <= score <= 1.0`

#### Scenario: Score a fault window
- **WHEN** a client requests `/anomaly` for the default tag set over a
  TEP fault-4 window
- **THEN** `alert == true`
- **AND** `score > 0.5`

### Requirement: SHAP explanations
The inference service SHALL expose `POST /explain { "alert_id": uuid }`
returning per-tag SHAP contributions for the alert. Explanations SHALL
be cached so identical alert ids do not recompute.

#### Scenario: Explain returns ranked contributions
- **WHEN** `/explain` is called with an alert id from the previous scenario
- **THEN** the response is a list of `{tag, contribution}` items sorted
  by absolute `contribution` descending
- **AND** the sum of absolute contributions equals the alert score
  within ±5%

### Requirement: Eval harness publishes AD benchmarks
`eval/anomaly_harness.py` SHALL evaluate the ensemble against at least 5
TEP fault scenarios, sweeping thresholds, and write
`{ "fault_id": int, "precision": float, "recall": float, "f1": float,
"threshold": float }` per scenario to `eval/results/anomaly.json`. The
harness SHALL fail with non-zero exit code if any scenario lacks results.

#### Scenario: Harness produces benchmark file
- **WHEN** `python eval/anomaly_harness.py --faults 1,4,6,8,11` runs
- **THEN** `eval/results/anomaly.json` contains one entry per fault
- **AND** every entry has numeric `precision`, `recall`, `f1`,
  `threshold` fields

### Requirement: Air-gapped operation
The AD worker, `/anomaly`, and `/explain` SHALL operate without any
outbound network calls. With `OFFLINE_MODE=1`, all components SHALL fail
fast at startup if any code path would attempt an external DNS lookup.

#### Scenario: Air-gapped scoring
- **WHEN** the worker starts with `OFFLINE_MODE=1` against a populated
  Timescale and Redpanda
- **THEN** scored rows appear in `tag_anomalies` within 60 seconds
- **AND** no DNS lookups beyond configured local services occur
