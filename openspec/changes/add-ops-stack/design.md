## Context

Noether is judged by two audiences (SPEC §2): hiring managers who will
read the README and try `docker compose up`, and learners who want a
clean reference. Both feel the ops layer first. The bar is "boring,
working, observable" — not "cutting-edge platform engineering".

k3d gives a single-binary k3s in Docker, ideal for the prod-style demo
without paying for managed K8s (SPEC §9 forbids EKS/GKE).

## Goals / Non-Goals

**Goals:**
- `docker compose up` cold-starts the full stack in <60 s after image
  pull (SPEC §10).
- `helm install noether ./charts/noether` deploys cleanly to k3d.
- Three values overlays: default, `dev`, `airgapped`.
- Every service exposes `/metrics`; Prometheus scrapes; Grafana shows.
- One Grafana dashboard per surface: ingest, storage, inference,
  agent, frontend.
- Evidently runs as a periodic job, writes drift reports to a volume,
  Grafana renders the summary.
- MLflow self-hosted with a Postgres backend (reuse Timescale's PG).
- GitHub Actions CI: lint → type → unit → integration (compose) →
  build → push to GHCR. Eval harnesses run on PRs that touch the
  relevant libs.

**Non-Goals (per SPEC §9 / SPEC §11):**
- Managed K8s (EKS/GKE).
- Service mesh, operators, CRDs.
- SealedSecrets (Kubernetes Secrets are sufficient at v0.1).
- Renovate bot until v0.1 ships (SPEC §11 — pin versions).

## Decisions

- **Compose:** single `docker-compose.yml` with profiles (`core`,
  `eval`) so users can run a slim dev set or the full stack including
  evaluation containers.
- **Helm:** one chart with sub-templates per service. Use the upstream
  Redpanda and Qdrant charts as dependencies via `Chart.yaml`
  `dependencies` to avoid maintaining their templates.
- **Observability:** `prometheus-client` for Python; OpenTelemetry SDK
  (auto-instrumented) for tracing into Grafana Tempo (optional, behind a
  feature flag — keep v0.1 small).
- **Metrics naming:** `<service>_<metric>` consistently;
  `service` label on every metric.
- **Evidently:** runs as a CronJob in Helm, a `cron`-profiled compose
  service in dev. Reports persisted to a `evidently/` volume.
- **MLflow:** image `ghcr.io/mlflow/mlflow`, backend store on the
  Timescale Postgres, artefact store on a local volume (or an OCI
  registry path in Helm).
- **CI/CD:** matrix on Python 3.11, Node 20. Compose-based integration
  tests use `docker compose up -d --wait`. Image build via
  `docker/build-push-action`.

## Risks / Trade-offs

- 60-second cold start budget is tight once Ollama and embedding models
  are involved. Mitigation: pre-bake images with model warmup;
  document that the budget is "after image pull" (SPEC §10 wording).
- Helm with subcharts increases values-file complexity. Mitigation: keep
  values flat at top level; document overlays.
- CI eval cost: harnesses can be slow. Mitigation: run them only on
  PRs touching the relevant libs (path filters); nightly run on `main`.
- SPEC §11: scope creep — no service mesh, no operators. We hold the line.
