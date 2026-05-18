# Noether Helm chart

Prod-style deployment of the full Noether stack to a single-node
**k3d/k3s** cluster (SPEC section 9 forbids managed K8s — this is the
local prod parity story).

```bash
k3d cluster create noether
helm install noether ./charts/noether                       # default
helm install noether ./charts/noether -f values.dev.yaml    # laptop
helm install noether ./charts/noether -f values.airgapped.yaml
```

`helm uninstall noether` removes everything (PVCs persist unless
`persistence.enabled=false`, the dev default).

## What it deploys

| Layer | Components |
|-------|------------|
| App   | ingest, storage-consumer, inference, anomaly-detector, agent, *(frontend — gated off until the service exists)* |
| Infra | Redpanda, TimescaleDB, Qdrant, Neo4j, Ollama |
| Ops   | Prometheus, Grafana (datasource + 6 dashboards), MLflow |

Everything is `ClusterIP`. The **only** Ingress is the frontend
(`ingress.enabled=true`, requires `services.frontend.enabled=true`) —
by design (spec: "Ingress for frontend; ClusterIP for everything else").

## Overlays

- **`values.yaml`** — default, persistent, prod-style resource envelope.
- **`values.dev.yaml`** — single replica, tiny requests, ephemeral
  storage, `IfNotPresent` pull (use `k3d image import`).
- **`values.airgapped.yaml`** — `OFFLINE_MODE=1` everywhere,
  NetworkPolicies on (default-deny + intra-release + cluster DNS),
  images referenced only via the `global.imageRegistry` mirror prefix.

## Why no subcharts

`design.md` floated upstream Redpanda/Qdrant subcharts. We template all
infrastructure in-chart instead:

1. **Air-gap mirror audit.** `tasks.md` 8.1 requires
   `values.airgapped.yaml` to reference only mirrored images. A single
   flat `images:` map (plus `image.*` for app services) is a one-screen
   audit; subchart image overrides are scattered across nested values.
2. **Verifiable "every Pod Ready".** The spec scenario asserts a clean
   k3d install with zero `CrashLoopBackOff`. Self-contained templates
   make that reproducible without a network `helm dependency build`.
3. **design.md itself flags subchart values-complexity as a risk.** We
   resolved it by removing the subcharts, not by absorbing the risk.

`Chart.yaml` carries no `dependencies:` block by design.

## Ordering / migrations

The Alembic migration runs as a `post-install,post-upgrade` Helm hook
(`hook-weight: 5`, after Timescale's StatefulSet). App pods carry a
`wait-for-deps` init container (busybox `nc` TCP probe on the timescale
image) so they don't crash-loop while infra comes up; a brief
pre-schema window is expected and within the 5-minute Ready budget.

## Storage

`inference` (ro) and `anomaly-detector` (rw) share one `ReadWriteOnce`
`model-store` PVC. On k3d (single node, `local-path` provisioner) both
pods schedule to the same node, so RWO is sufficient. `anomaly-detector`
uses a `Recreate` strategy to avoid two pods racing the volume during
rollouts. Multi-node prod would need RWX (out of scope for v0.1).

## Grafana dashboards

`charts/noether/dashboards/*.json` are vendored copies of
`infra/grafana/provisioning/dashboards/files/*.json` (Helm cannot read
files outside the chart root). Keep them in sync — a `make sync-dashboards`
target lands in phase 4c. They are mounted via a ConfigMap built with
`.Files.Glob`.

## Lint

```bash
helm lint charts/noether
helm template noether charts/noether                          # default
helm template noether charts/noether -f charts/noether/values.airgapped.yaml
```

CI runs all three on every PR (`helm-lint` job).
