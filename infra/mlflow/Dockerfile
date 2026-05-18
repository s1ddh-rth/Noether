# syntax=docker/dockerfile:1.7
# Self-hosted MLflow tracking server (add-ops-stack task 5).
#
# A purpose-built image rather than a runtime `pip install` so the
# Postgres driver is baked at build time — runtime stays air-gapped
# (OFFLINE_MODE / values.airgapped.yaml), honouring the SPEC's
# zero-outbound-call rule while still using a Postgres backend store.
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
      "mlflow==2.18.0" \
      "psycopg2-binary==2.9.10"

# Artefact root; backed by a named volume in compose / a PVC in Helm.
RUN mkdir -p /mlflow/artifacts && chown -R 1001:1001 /mlflow

EXPOSE 5000
USER 1001:1001

# backend-store-uri and artifact root are supplied by compose/Helm so the
# same image works for both; default to a local sqlite fallback if unset
# (keeps `docker run` of the bare image usable for debugging).
ENTRYPOINT ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
