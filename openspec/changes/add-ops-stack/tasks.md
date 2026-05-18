## 1. Compose

- [ ] 1.1 Consolidate `docker-compose.yml` with profiles (`core`, `eval`,
      `cron`)
- [x] 1.2 Add Prometheus, Grafana, MLflow services (phase 4a — Grafana
      pre-existed from M1; Prometheus + MLflow added here)
- [ ] 1.3 Cold-start budget verified: <60 s after image pull
- [ ] 1.4 `make up`, `make down`, `make logs` targets

## 2. Helm chart

- [x] 2.1 `charts/noether/Chart.yaml` — infra templated in-chart
      (Redpanda, TimescaleDB, Qdrant, Neo4j, Ollama) instead of subchart
      deps. Rationale in `charts/noether/README.md` ("Why no subcharts"):
      a flat image list is required for the air-gap mirror audit (8.1)
      and self-contained templates make the "every Pod Ready" guarantee
      verifiable without a network `helm dependency build`. design.md
      itself flagged subchart values-complexity as the risk we removed.
- [x] 2.2 Templates per service: ingest, storage-consumer, inference,
      anomaly-detector, agent. Frontend Deployment/Service/Ingress ship
      gated `enabled: false` (services/frontend doesn't exist yet — it's
      the separate add-frontend-dashboard change); flip the flag when it
      lands. Ops workloads (Prometheus, Grafana, MLflow) templated too.
- [x] 2.3 `values.yaml` (default), `values.dev.yaml`,
      `values.airgapped.yaml` — all three lint + template clean.
- [x] 2.4 Ingress only for frontend (with a fail-guard when
      `ingress.enabled` without `frontend.enabled`); every other
      component is ClusterIP.
- [x] 2.5 NetworkPolicies (default-deny + intra-release + cluster DNS)
      gated by `networkPolicy.enabled`, set true in
      `values.airgapped.yaml`.

## 3. Observability

- [x] 3.1 `prometheus-client` integration in every Python service —
      agent had it from M3; inference gets a /metrics route + request
      middleware; the three workers expose it via the shared
      `noether_ingest.metrics.start_metrics_server` helper.
- [x] 3.2 `prometheus.yml` with all scrape targets (one config spans
      core/eval/agent; off-profile targets read as `down`)
- [x] 3.3 Grafana provisioning: Prometheus datasource + dashboards
      from `infra/grafana/provisioning/dashboards/files/`
- [x] 3.4 5 starter dashboards — platform-overview, inference, agent,
      ingest, storage-consumer (no "frontend" dashboard: the frontend
      exposes no metrics in v0.1; overview takes that slot)

## 4. Drift monitoring

- [ ] 4.1 `evidently/config.yaml` with reference window definition
- [ ] 4.2 Cron job (compose `cron` profile, Helm CronJob) computing
      drift and writing JSON reports
- [ ] 4.3 Grafana panel reading the latest drift report

## 5. MLflow

- [x] 5.1 MLflow server image in compose + Helm — compose done (custom
      image, driver baked for air-gap); Helm Deployment/Service/PVC
      landed in phase 4b (backend store on the in-cluster Timescale
      `mlflow` DB, artefacts on a PVC).
- [x] 5.2 Backend store on Timescale Postgres (separate `mlflow`
      database, created by an idempotent initdb script)
- [x] 5.3 Artefact store on the mlflow-artifacts volume (configurable
      via `--artifacts-destination`)
- [x] 5.4 Document `MLFLOW_TRACKING_URI` env wiring (.env.example)

## 6. CI/CD

- [ ] 6.1 `.github/workflows/ci.yml`: lint, type, unit, integration,
      build, push (main only)
- [ ] 6.2 Path-filtered eval jobs: forecast harness, AD harness, RAGAS
- [ ] 6.3 Render benchmark Markdown into `docs/benchmarks.md` and
      open a PR if changed (nightly)
- [ ] 6.4 GHCR push with semver tag on release; `:latest` on main

## 7. Tests

- [ ] 7.1 Compose smoke test (every healthcheck passes within budget)
- [~] 7.2 `helm lint` + `helm template` (all 3 overlays) + kubeconform
      schema validation run in CI (`helm-lint` job). `helm install`
      against a real k3d cluster in CI lands in phase 4c.
- [ ] 7.3 Air-gapped overlay verified in CI by blocking egress in a
      kind/k3d network policy

## 8. Air-gap

- [ ] 8.1 `values.airgapped.yaml` references only mirrored images
- [ ] 8.2 OFFLINE_MODE=1 set in airgapped overlay everywhere
- [ ] 8.3 Documentation of mirror procedure in `docs/deployment.md`

## 9. Eval / Benchmarks

- [ ] 9.1 Nightly job runs all three harnesses and updates
      `docs/benchmarks.md`

## 10. Docs

- [ ] 10.1 `docs/deployment.md`: compose, Helm, k3d, air-gapped path
- [ ] 10.2 README finalised: hero GIF, badges, capabilities, quickstart,
      benchmarks, deployment, roadmap
- [ ] 10.3 3-minute Loom video link embedded in README
- [ ] 10.4 LICENSE (Apache 2.0) and CONTRIBUTING.md committed
- [ ] 10.5 Tag `v0.1.0`
