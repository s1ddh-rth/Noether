# Deployment

## Local (docker compose)

Prereqs: Docker 24+, Docker Compose v2.

```
cp .env.example .env
make up          # docker compose --profile core up -d
make logs        # tail all services
```

Services exposed on the host:
- Redpanda Kafka API: `localhost:9092`
- Redpanda admin: `localhost:9644`
- TimescaleDB: `localhost:5432`
- Inference API: `localhost:8000`
- Grafana: `localhost:3000` (admin / admin by default)

```
make down        # tear down + remove volumes
make eval        # run the forecast harness once
```

## k3d (Helm)

Helm chart lands in M4. Outline:

```
charts/noether/
├── Chart.yaml             # subcharts: redpanda, timescaledb, qdrant, neo4j
├── values.yaml            # default
├── values.dev.yaml        # local k3d overrides
└── values.airgapped.yaml  # registry-mirrored images, NetworkPolicies
```

## Air-gapped

`OFFLINE_MODE=1` is the default in `.env.example`. Ensures no service does
DNS lookups or HTTP calls outside the cluster network. Cloud LLM keys
(`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) are blank by
default and are only consulted when `LLM_BACKEND` is non-default.
