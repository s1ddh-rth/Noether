## Why

Streaming anomaly detection with explainability is a headline capability
(SPEC §3 (4) and (5)) and the focus of Milestone 2 (SPEC §8). Definition
of done requires precision/recall/F1 across at least 5 TEP fault scenarios
published to `docs/benchmarks.md` (SPEC §10).

This change introduces the AD library, the streaming inference loop, the
SHAP-based explainability layer, the `/anomaly` and `/explain` endpoints
on the inference service, and the eval harness — all named in
SPEC §4 (component 4).

## What Changes

- Add `libs/anomaly/` with: feature builder shared with forecasting,
  PyOD-backed Isolation Forest + autoencoder + Mahalanobis detectors, an
  EWMA control-chart detector, an ensemble scorer, and a SHAP-based
  explainer.
- Add a streaming AD worker that consumes `plant.tags` and emits scored
  anomaly events to a new `plant.anomalies` topic and to TimescaleDB.
- Extend `services/inference/` with `POST /anomaly` (score a window) and
  `POST /explain` (return SHAP attributions for an alert).
- Add `eval/anomaly_harness.py` running TEP fault scenarios and writing
  precision/recall/F1 to `eval/results/anomaly.json`.

## Capabilities

### New Capabilities
- `anomaly-detection`: Stream-score plant tag windows with an ensemble of
  multivariate detectors, persist scored events, and produce SHAP-based
  explanations on demand.

### Modified Capabilities
- `forecasting-service`: extends the `services/inference/` API surface
  with two additional endpoints (`/anomaly`, `/explain`). Endpoint
  ownership is shared; no behaviour of `/forecast` changes.

## Impact

- New code: `libs/anomaly/`, streaming worker under
  `services/inference/anomaly_worker.py`, two new endpoints on the same
  FastAPI app.
- New deps (justified): `pyod` (SPEC §5), `shap` (SPEC §5), `torch`
  (already in stack for PatchTST; reused for the autoencoder), `numpy`,
  `scikit-learn` (already implied).
- New Kafka topic `plant.anomalies`; storage consumer extended (or a new
  consumer) to persist alerts to a `tag_anomalies` table.
- Eval depends on the labelled fault profiles produced by the ingest
  service (`add-ingest-pipeline`).
- Out of scope: PINNs, custom novelty algorithms, root-cause graph search
  (v0.2).
