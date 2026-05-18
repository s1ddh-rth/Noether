# Deployment

Three supported paths, smallest to largest:

1. **docker compose** — laptop dev / the `docker compose up` demo.
2. **k3d + Helm** — prod-style single-node Kubernetes.
3. **Air-gapped** — no-egress install from a mirrored registry.

The default configuration runs with **zero paid services and zero
outbound network calls** (`LLM_BACKEND=ollama`, `OFFLINE_MODE=1`).

---

## 1. Local (docker compose)

Prereqs: Docker 24+, Docker Compose v2.

```bash
cp .env.example .env
make up          # docker compose --profile core up -d
make logs        # tail all services
make ps          # container status
make down        # tear down + remove volumes
```

Profiles (compose):

| Profile | Adds |
|---------|------|
| `core`  | ingest, storage-consumer, inference, anomaly-detector, Redpanda, TimescaleDB, Prometheus, Grafana |
| `eval`  | one-shot forecast / anomaly eval containers + MLflow |
| `agent` | Neo4j, Ollama, Qdrant, the agent service, MLflow |
| `rag`   | Qdrant (for the `libs/rag` pipeline) |
| `cron`  | the Evidently drift monitor (loops the one-shot job) |

Combine profiles, e.g. the full demo + drift:

```bash
docker compose --profile agent --profile cron up -d
docker exec -it noether-ollama ollama pull llama3.2:3b   # one-time
```

Host ports: Inference `:8000`, Agent `:8100`, Grafana `:3000`
(anonymous viewer on), Prometheus `:9090`, MLflow `:5000`,
TimescaleDB `:5432`, Redpanda `:9092`.

`make drift` runs the drift job once; `make eval` runs the forecast
harness.

---

## 2. k3d + Helm (prod-style)

Prereqs: Docker, [k3d](https://k3d.io) 5.x, `kubectl`, Helm 3.13+.
SPEC section 9 forbids managed K8s — k3d gives single-binary k3s in
Docker for local prod parity.

```bash
k3d cluster create noether
helm install noether ./charts/noether                          # default
helm install noether ./charts/noether -f charts/noether/values.dev.yaml
kubectl get pods -w
```

The chart deploys every service plus its infrastructure (Redpanda,
TimescaleDB, Qdrant, Neo4j, Ollama) and ops (Prometheus, Grafana,
MLflow, the drift CronJob). See `charts/noether/README.md` for the
component table, the storage/persistence model, and the
"why no subcharts" rationale.

Overlays:

| File | Use |
|------|-----|
| `values.yaml` | default, persistent, prod-style resources |
| `values.dev.yaml` | single replica, tiny requests, **ephemeral** storage (`emptyDir`), `IfNotPresent` pull |
| `values.airgapped.yaml` | `OFFLINE_MODE=1`, mirror-only images, NetworkPolicies on |

Everything is `ClusterIP`. The only Ingress is the frontend
(`--set ingress.enabled=true`, requires `services.frontend.enabled=true`
once that service exists). Reach services meanwhile via
`kubectl port-forward` (the post-install notes print the exact
commands).

Local images on k3d:

```bash
docker compose build                       # or build individual services
k3d image import noether-inference:latest -c noether   # repeat per image
helm install noether ./charts/noether -f charts/noether/values.dev.yaml \
  --set image.pullPolicy=Never
```

CI proves this path on every PR (`k3d-e2e` job): a real k3d cluster,
`helm install`, and an assertion that every Pod is Ready with zero
`CrashLoopBackOff`.

---

## 3. Air-gapped

`OFFLINE_MODE=1` (default in `.env.example` and the airgapped overlay)
forbids any DNS/HTTP outside the cluster network. Cloud LLM keys
(`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) are blank by
default and only consulted when `LLM_BACKEND` is non-default.

### Mirror procedure

`values.airgapped.yaml` references **only** images under
`global.imageRegistry`. The full image set is a one-screen audit — the
flat `images:` map plus the app `image.*` (this is the reason the chart
templates infra in-chart rather than using subcharts).

1. **Enumerate** the images to mirror:

   ```bash
   helm template noether ./charts/noether \
     -f charts/noether/values.airgapped.yaml \
     | grep -oE 'image: \S+' | sort -u
   ```

   That is: the seven `noether-*` application/ops images
   (`ingest`, `storage-consumer`, `inference`, `anomaly-detector`,
   `agent`, `mlflow`, `drift`) plus the infrastructure images
   (`redpanda`, `timescaledb`, `qdrant`, `neo4j`, `ollama`,
   `prometheus`, `grafana`) pinned in `values.yaml` `images:`.

2. **Build + push** the `noether-*` images to your internal registry
   (CI publishes them to GHCR on `main`/release tags; in an air-gap you
   re-tag and push to the mirror):

   ```bash
   MIRROR=registry.internal      # your in-cluster / on-prem registry
   for svc in ingest storage-consumer inference anomaly-detector agent; do
     docker build -f services/$svc/Dockerfile -t $MIRROR/noether-$svc:0.1.0 .
     docker push $MIRROR/noether-$svc:0.1.0
   done
   docker build -f infra/mlflow/Dockerfile -t $MIRROR/noether-mlflow:0.1.0 .
   docker build -f infra/drift/Dockerfile  -t $MIRROR/noether-drift:0.1.0 .
   docker push $MIRROR/noether-mlflow:0.1.0
   docker push $MIRROR/noether-drift:0.1.0
   ```

3. **Mirror the infra images** (skopeo, or pull / tag / push):

   ```bash
   for img in redpandadata/redpanda:v24.2.18 \
              timescale/timescaledb:2.17.2-pg16 \
              qdrant/qdrant:v1.13.0 neo4j:5.26-community \
              ollama/ollama:0.5.4 prom/prometheus:v3.0.1 \
              grafana/grafana-oss:11.3.1; do
     skopeo copy docker://$img docker://$MIRROR/$img
   done
   ```

4. **Install** pointing at the mirror (trailing slash required):

   ```bash
   helm install noether ./charts/noether \
     -f charts/noether/values.airgapped.yaml \
     --set global.imageRegistry=$MIRROR/
   ```

The airgapped overlay turns on NetworkPolicies (default-deny +
intra-release + cluster DNS only). CI's `k3d-e2e` job proves this:
after install it applies the airgapped NetworkPolicies and asserts a
release-labelled pod **cannot** reach the public internet.

---

## Observability

Grafana provisions a Prometheus datasource and the dashboards in
`infra/grafana/provisioning/dashboards/files/` (vendored into the chart
under `charts/noether/dashboards/`): platform-overview, inference,
agent, ingest, storage-consumer, plant-tags, and **input-drift** (reads
the `drift_reports` table via the TimescaleDB datasource).
