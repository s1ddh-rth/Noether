## 1. Compose

- [x] 1.1 Single `docker-compose.yml` with `core` / `eval` / `cron`
      profiles (plus `rag` / `agent` from M3). `cron` adds the Evidently
      drift monitor (loops the one-shot job).
- [x] 1.2 Add Prometheus, Grafana, MLflow services (phase 4a — Grafana
      pre-existed from M1; Prometheus + MLflow added here)
- [~] 1.3 Cold-start observed well under budget after image pull
      (this session: timescaledb/redpanda healthy ~27 s, inference
      healthy ~16 s on `--profile core --profile cron up -d`). A
      formal timed assertion in CI lands with the k3d/integration
      work in 4d.
- [x] 1.4 `make up` / `down` / `logs` / `ps` (+ `drift`) targets;
      `down` now spans core/eval/cron/agent profiles.

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

- [x] 4.1 `evidently/config.yaml` (reference/current windows, tags,
      drift gate) loaded + validated by `noether_drift.DriftConfig`.
- [x] 4.2 `libs/drift` (`noether-drift`): one-shot job pulls two
      windows from Timescale, runs Evidently `DataDriftPreset`, writes
      full JSON to a volume + a summary row to `drift_reports`. Run by
      the compose `cron` loop and a Helm `CronJob` (`infra/drift/
      Dockerfile`). 9 unit tests.
- [x] 4.3 Grafana "Noether — Input Drift" dashboard reads
      `drift_reports` via the TimescaleDB datasource (stable
      `uid: TimescaleDB`). Verified end-to-end against the running
      stack with Playwright (verdict / share / table panels render a
      real row).

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

- [x] 6.1 `ci.yml`: lint (black+ruff) · type (mypy, scoped to
      `libs/drift/noether_drift` — typing-debt ratchet noted in-job) ·
      unit (pytest) · integration (compose smoke + k3d e2e) · build
      (7-image matrix) · push to GHCR on `push`/main.
- [x] 6.2 `eval.yml`: `dorny/paths-filter` gates the forecast harness
      (libs/forecasting, services/inference) and anomaly harness
      (libs/anomaly, services/anomaly-detector) so they run only when
      that area changes; schedule/dispatch force-run both. (RAGAS needs
      Qdrant + an LLM corpus — out of the air-gap default; its skeleton
      is exercised by `eval/tests`, full RAGAS is a post-v0.1 follow-up.)
- [x] 6.3 Nightly job renders `eval/render_benchmarks.py` into the
      AUTO-marked block of `docs/benchmarks.md` and opens a PR via
      `peter-evans/create-pull-request` if it changed.
- [x] 6.4 `docker/metadata-action`: `:latest` on main, `:sha`, and
      `{{version}}`/`{{major}}.{{minor}}` semver on release tags;
      pushes only on `push` events (PRs build-only, no creds).

## 7. Tests

- [x] 7.1 `compose smoke` job builds the core stack and waits until
      every healthcheck is healthy / running (migrator exits 0) within
      the timeout budget.
- [x] 7.2 `helm lint` + `helm template` (3 overlays) + kubeconform
      (`helm-lint`) **and** a real `k3d-e2e` job: k3d cluster +
      `helm install` (infra + ops subset — public images, keeps the
      run in budget; app images covered by compose smoke + the
      `images` job) + assert every Pod Ready, zero CrashLoopBackOff.
- [x] 7.3 `k3d-e2e` applies the airgapped-overlay NetworkPolicies
      over the release and proves a release-labelled pod cannot reach
      the public internet (egress blocked → step fails if it can).

## 8. Air-gap

- [x] 8.1 `values.airgapped.yaml` references only mirror-prefixed
      images (verified in 4b: every app + infra + drift/mlflow image
      renders under `global.imageRegistry`).
- [x] 8.2 `OFFLINE_MODE=1` + mirror prefix set in the airgapped
      overlay (4b); drift job inherits it via `commonEnv`.
- [x] 8.3 `docs/deployment.md` §3 "Air-gapped → Mirror procedure":
      enumerate-images command, build/push the `noether-*` images,
      `skopeo` the infra images, install with `global.imageRegistry`.

## 9. Eval / Benchmarks

- [x] 9.1 Nightly `eval.yml` runs the forecast + anomaly harnesses
      (full) and refreshes `docs/benchmarks.md` via PR. RAGAS excluded
      (needs Qdrant + LLM corpus, out of the air-gap default) — noted
      under 6.2 as a post-v0.1 follow-up.

## 10. Docs

- [x] 10.1 `docs/deployment.md` rewritten: compose (profiles table) ·
      k3d + Helm (overlays, local-image flow, the CI proof) ·
      air-gapped (mirror procedure).
- [x] 10.2 README finalised: capabilities updated for M4, deployment
      pointer, roadmap marks M3/M4 shipped, OpenSpec status table
      corrected. (Hero GIF / recorded demo are a human follow-up —
      see 10.3.)
- [~] 10.3 A recorded walk-through needs a human in front of the live
      stack; CI cannot produce it. Documented in the README as an
      explicit post-v0.1 follow-up rather than shipping a dead link.
- [x] 10.4 `LICENSE` (Apache 2.0) and `CONTRIBUTING.md` present at
      repo root (committed in earlier milestones; verified).
- [ ] 10.5 Tag `v0.1.0` — a release tag is cut from `main` **after**
      this PR merges and `openspec archive add-ops-stack` runs. It
      must not be tagged from the feature branch; this is the documented
      final release step, executed post-merge.
