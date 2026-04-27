## Context

TEP gives 20 standard fault profiles plus a no-fault baseline. Real
industrial AD systems combine several detector families because no single
detector covers all fault classes well: tree-based novelty (Isolation
Forest), reconstruction error (autoencoder), distance-based (Mahalanobis),
and statistical control charts (EWMA). PyOD wraps the first three; EWMA
is a 30-line implementation.

Explainability is a hard requirement (SPEC §3 (5)). SHAP works directly
on the LightGBM-friendly feature representation and gives per-feature
attribution that the LLM agent can summarise.

## Goals / Non-Goals

**Goals:**
- One `Detector` interface; PyOD-backed implementations + EWMA.
- Ensemble scorer producing a single 0-1 score and a per-detector
  breakdown.
- Streaming worker reads windows from Timescale (not Kafka) so windows
  are easy to assemble and test.
- SHAP explanations attached to every alert above threshold.
- Eval harness reports precision, recall, F1 per fault scenario; targets
  ≥ 5 scenarios per SPEC §10.

**Non-Goals (per SPEC §9):**
- Root-cause graph search.
- Novel detector algorithms beyond PyOD primitives.
- Real-time websocket alert push (the worker writes events; the frontend
  polls — SPEC §9).

## Decisions

- **Service structure:** this change drops in two new routers under
  `services/inference/routers/` (`anomaly.py`, `explain.py`) and a
  background worker under `services/inference/anomaly_worker.py`. The
  `services/inference/app.py` from `add-forecasting-service` was built
  with `include_router(...)` from day one, so adding endpoints here is
  a one-line `app.include_router(...)` change — no refactor of an
  existing monolithic main file. The worker runs as a separate process
  in the same image (compose service `inference-worker`).
- **Window:** sliding 60-second window (60 samples per tag at 1 Hz),
  stride 5 seconds. Windowing happens in the worker, not the API, so the
  endpoint is stateless.
- **Detectors:** PyOD `IForest`, `AutoEncoder` (PyTorch backend), `MCD`
  (Mahalanobis). EWMA implemented in `libs/anomaly/ewma.py`.
- **Ensemble:** mean of per-detector z-scaled scores. Threshold tuned per
  fault profile during eval; default operating point at validation F1
  optimum.
- **Storage:** `tag_anomalies (ts TIMESTAMPTZ, score DOUBLE PRECISION,
  detectors JSONB, tags TEXT[], shap JSONB)`. Hypertable on `ts`.
- **SHAP:** computed at alert time, not for every score, to keep cost
  bounded. `KernelExplainer` for the autoencoder, `TreeExplainer` for
  IForest, surrogate model for MCD/EWMA.
- **Topic:** alerts go to `plant.anomalies` for the agent system to
  subscribe to (loose coupling).
- **Endpoint contract:** `POST /anomaly { "tags": [...], "start": ts,
  "end": ts }` returns score breakdown for the window. `POST /explain {
  "alert_id": uuid }` returns SHAP attributions.

## Risks / Trade-offs

- KernelExplainer is slow; document compute budget and accept it for
  v0.1 since explanations only run on alerts.
- Ensemble simple mean isn't optimal but matches "boring tech wins"
  (SPEC §11). Stacking can land in v0.2.
- Windowing in the worker creates duplicated logic if we ever want
  on-demand scoring of arbitrary windows from the API. We accept that
  duplication; alternative (Kafka Streams) is heavier than v0.1 needs.
