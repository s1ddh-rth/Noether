## Why

The deployment story is a first-class capability of Noether (SPEC §3 (9))
— `docker compose up` for dev, Helm on k3s for prod-style. Observability
(Prometheus + Grafana), drift monitoring (Evidently), experiment tracking
(MLflow), and a working CI/CD pipeline are all definition-of-done items
(SPEC §10). SPEC §4 (component 8) groups these under "Ops".

This change is the focus of Milestone 4 (SPEC §8) and depends on every
other change shipping first.

## What Changes

- `docker-compose.yml` consolidated and verified end-to-end (cold start
  under 60 s after image pull — SPEC §10).
- `charts/noether/` Helm chart deploying every service to k3d cleanly,
  with `values.yaml`, `values.dev.yaml`, `values.airgapped.yaml`.
- Prometheus + Grafana containers; pre-built dashboards committed.
- Evidently AI integration for input/prediction drift.
- MLflow tracking server self-hosted in compose and Helm.
- GitHub Actions CI/CD: lint, type-check, test, build images, push to
  GHCR, run eval harnesses, render benchmark Markdown.

## Capabilities

### New Capabilities
- `ops-stack`: Provide a cohesive dev (compose) and prod-style (Helm
  on k3d) deployment with observability, drift monitoring, experiment
  tracking, and CI/CD that builds, tests, and publishes the project.

### Modified Capabilities
- All services gain Prometheus exporters (no API change to those
  services; only metrics surface added).

## Impact

- New code: `charts/noether/` (Helm), `.github/workflows/ci.yml`,
  `grafana/dashboards/*.json`, `prometheus/prometheus.yml`,
  `evidently/` configuration.
- New deps: none for application code beyond client libs already
  introduced (`prometheus-client` for Python, etc.).
- New infra in compose/Helm: Prometheus, Grafana, MLflow, k3d compatible
  ingress.
- Docs: `docs/deployment.md`, README finalisation (hero GIF, badges,
  benchmarks tables).
- Out of scope: managed K8s (EKS/GKE), service mesh, operators/CRDs,
  SealedSecrets (SPEC §9 / SPEC §11).
