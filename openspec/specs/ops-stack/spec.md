# ops-stack Specification

## Purpose
TBD - created by archiving change add-ops-stack. Update Purpose after archive.
## Requirements
### Requirement: Compose cold-start budget
`docker compose up` against pre-pulled images SHALL bring the full
stack to a healthy state within 60 seconds on a laptop-class machine
(8 cores, 16 GB RAM). "Healthy" SHALL be defined as every service
returning 200 from its `/health` endpoint or its container healthcheck
returning healthy.

#### Scenario: Cold start under budget
- **WHEN** all images are present locally and `docker compose up -d
  --wait` is invoked
- **THEN** the command exits 0 within 60 seconds

### Requirement: Helm chart deploys to k3d
A single `helm install noether ./charts/noether` command SHALL deploy
the full stack to a k3d cluster cleanly (every Pod becomes Ready). The
chart SHALL ship three values overlays: `values.yaml` (default),
`values.dev.yaml`, `values.airgapped.yaml`.

#### Scenario: Default install on k3d
- **WHEN** `k3d cluster create noether && helm install noether
  ./charts/noether` is run
- **THEN** within 5 minutes every Pod is in `Running` state and Ready
- **AND** `kubectl get pods` reports zero `CrashLoopBackOff`

#### Scenario: Air-gapped overlay
- **WHEN** the cluster has no outbound network and `helm install
  noether ./charts/noether -f values.airgapped.yaml` is run with
  required images pre-loaded
- **THEN** the install succeeds and every Pod becomes Ready

### Requirement: Prometheus + Grafana observability
Every service SHALL expose a Prometheus `/metrics` endpoint with
service-prefixed metric names. Prometheus SHALL scrape all services.
Grafana SHALL ship pre-built dashboards for ingest, storage, inference,
agent, and frontend, committed under `grafana/dashboards/`.

#### Scenario: Service metrics scraped
- **WHEN** the compose stack is up
- **THEN** `curl http://localhost:9090/api/v1/query?query=up` returns
  `value=1` for every service target

#### Scenario: Grafana dashboards present
- **WHEN** Grafana is opened
- **THEN** at least 5 dashboards are listed under the "Noether" folder

### Requirement: Drift monitoring with Evidently
An Evidently job SHALL run periodically (compose profile `cron`,
Helm CronJob) computing drift between the current ingest window and a
reference baseline, and writing reports to a persistent volume. A
Grafana dashboard SHALL surface the latest drift summary.

#### Scenario: Drift report generated
- **WHEN** the Evidently job has run at least once against a populated
  Timescale
- **THEN** a JSON report exists at the configured location
- **AND** the Grafana drift dashboard renders a non-empty summary panel

### Requirement: MLflow tracking
An MLflow tracking server SHALL run as part of the stack. All training
runs from `libs/forecasting` and `libs/anomaly` SHALL log to it. The
backend store SHALL be the Timescale Postgres instance; the artefact
store SHALL be a local volume in dev and a configurable path in Helm.

#### Scenario: Training run is tracked
- **WHEN** `python -m libs.forecasting.train --tag XMEAS_7` runs
  against the compose stack
- **THEN** a new MLflow run is visible in the MLflow UI with params,
  metrics, and a model artefact

### Requirement: GitHub Actions CI/CD
The repository SHALL have a CI workflow that on every PR runs: lint
(ruff, prettier, eslint), type-check (mypy strict), unit tests
(pytest, vitest), integration tests (`docker compose up -d --wait`),
relevant eval harnesses (path-filtered), image build, and (on `main`)
image push to GHCR.

#### Scenario: PR runs full CI
- **WHEN** a PR is opened touching `libs/forecasting/`
- **THEN** the workflow runs lint, type, unit, integration, and the
  forecast eval harness
- **AND** the workflow status is reported on the PR

### Requirement: Air-gapped end-to-end
With `LLM_BACKEND=ollama` and `OFFLINE_MODE=1`, the entire stack SHALL
operate without any outbound network calls. Helm `values.airgapped.yaml`
SHALL set these values, disable any external scrape targets, and
reference only locally-mirrored images.

#### Scenario: Air-gapped install operates
- **WHEN** the air-gapped overlay is installed and a tag stream is
  flowing
- **THEN** the demo agent question succeeds end-to-end
- **AND** no DNS lookups beyond cluster-internal services occur

