## 1. Scaffolding

- [ ] 1.1 Create `libs/anomaly/` with `pyproject.toml` and `README.md`
- [ ] 1.2 Add `services/inference/anomaly_worker.py` entrypoint and
      Dockerfile target
- [ ] 1.3 Pin `pyod`, `shap`, `torch` (already present), and
      `scikit-learn` in workspace

## 2. Detectors

- [ ] 2.1 `Detector` Protocol in `libs/anomaly/protocol.py`
- [ ] 2.2 PyOD `IForest` wrapper
- [ ] 2.3 PyOD `AutoEncoder` (PyTorch backend) wrapper
- [ ] 2.4 PyOD `MCD` (Mahalanobis) wrapper
- [ ] 2.5 EWMA control-chart detector
- [ ] 2.6 Ensemble scorer (z-scaled mean) returning `score` + breakdown

## 3. Streaming worker

- [ ] 3.1 Window assembly from Timescale: 60-sample window, 5s stride
- [ ] 3.2 Per-window scoring loop
- [ ] 3.3 Persist to `tag_anomalies` (new Alembic migration)
- [ ] 3.4 Publish to `plant.anomalies` when `score > threshold`

## 4. Endpoints

- [ ] 4.1 `services/inference/routers/anomaly.py` with `POST /anomaly`
      Pydantic models + handler
- [ ] 4.2 `services/inference/routers/explain.py` with `POST /explain`
      handler and SHAP cache (LRU, 1000 entries)
- [ ] 4.3 Mount both routers in `services/inference/app.py` via
      `include_router(...)` (one-line additions; no refactor of `app.py`)
- [ ] 4.4 SHAP per-detector: TreeExplainer (IForest), KernelExplainer
      (AutoEncoder), surrogate (MCD/EWMA)

## 5. Eval harness

- [ ] 5.1 `eval/anomaly_harness.py` runs against >= 5 TEP faults
- [ ] 5.2 Threshold sweep, picks F1 optimum per fault
- [ ] 5.3 Writes `eval/results/anomaly.json`
- [ ] 5.4 Renders Markdown table into `docs/benchmarks.md`

## 6. Observability

- [ ] 6.1 Counter `anomaly_alerts_total{fault_class}`
- [ ] 6.2 Histogram `anomaly_score_ms`
- [ ] 6.3 Histogram `anomaly_explain_ms`
- [ ] 6.4 Gauge `anomaly_threshold_current`

## 7. Tests

- [ ] 7.1 Unit: each detector returns shape-correct scores
- [ ] 7.2 Unit: ensemble respects per-detector contribution sum bound
- [ ] 7.3 Integration: ingest fault-4 trace, worker emits alert in
      `plant.anomalies` within 60 seconds
- [ ] 7.4 API: `/anomaly` and `/explain` happy paths
- [ ] 7.5 Coverage >=70% on `libs/anomaly/` and worker code

## 8. Air-gap

- [ ] 8.1 No outbound DNS at runtime; verified under `OFFLINE_MODE=1`

## 9. Eval / Benchmarks

- [ ] 9.1 First AD benchmarks committed to `docs/benchmarks.md`
- [ ] 9.2 CI re-runs harness on PRs touching `libs/anomaly/`

## 10. Docs

- [ ] 10.1 `libs/anomaly/README.md`: detector contract, ensemble math
- [ ] 10.2 `services/inference/README.md` updated with `/anomaly` and
      `/explain`
- [ ] 10.3 AD section added to `docs/architecture.md`
