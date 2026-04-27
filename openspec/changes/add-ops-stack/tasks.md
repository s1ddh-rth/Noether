## 1. Compose

- [ ] 1.1 Consolidate `docker-compose.yml` with profiles (`core`, `eval`,
      `cron`)
- [ ] 1.2 Add Prometheus, Grafana, MLflow services
- [ ] 1.3 Cold-start budget verified: <60 s after image pull
- [ ] 1.4 `make up`, `make down`, `make logs` targets

## 2. Helm chart

- [ ] 2.1 `charts/noether/Chart.yaml` with Redpanda, Qdrant, TimescaleDB
      subchart deps
- [ ] 2.2 Templates per service: ingest, storage-consumer, inference,
      agent, frontend
- [ ] 2.3 `values.yaml` (default), `values.dev.yaml`,
      `values.airgapped.yaml`
- [ ] 2.4 Ingress for frontend; ClusterIP for everything else
- [ ] 2.5 NetworkPolicies in `values.airgapped.yaml`

## 3. Observability

- [ ] 3.1 `prometheus-client` integration in every Python service
- [ ] 3.2 `prometheus.yml` with all scrape targets
- [ ] 3.3 Grafana provisioning: datasource + dashboards from
      `grafana/dashboards/`
- [ ] 3.4 5 starter dashboards (ingest, storage, inference, agent, frontend)

## 4. Drift monitoring

- [ ] 4.1 `evidently/config.yaml` with reference window definition
- [ ] 4.2 Cron job (compose `cron` profile, Helm CronJob) computing
      drift and writing JSON reports
- [ ] 4.3 Grafana panel reading the latest drift report

## 5. MLflow

- [ ] 5.1 MLflow server image in compose + Helm
- [ ] 5.2 Backend store on Timescale Postgres (separate database)
- [ ] 5.3 Artefact store on local volume / configurable path
- [ ] 5.4 Document `MLFLOW_TRACKING_URI` env wiring

## 6. CI/CD

- [ ] 6.1 `.github/workflows/ci.yml`: lint, type, unit, integration,
      build, push (main only)
- [ ] 6.2 Path-filtered eval jobs: forecast harness, AD harness, RAGAS
- [ ] 6.3 Render benchmark Markdown into `docs/benchmarks.md` and
      open a PR if changed (nightly)
- [ ] 6.4 GHCR push with semver tag on release; `:latest` on main

## 7. Tests

- [ ] 7.1 Compose smoke test (every healthcheck passes within budget)
- [ ] 7.2 `helm template` lints; `helm install` against a real k3d in CI
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
