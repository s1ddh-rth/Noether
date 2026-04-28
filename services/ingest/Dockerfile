# syntax=docker/dockerfile:1.7
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.6 /uv /usr/local/bin/uv

WORKDIR /app

# Copy only manifests first to maximise layer cache hits.
COPY pyproject.toml ./
COPY libs/ingest/pyproject.toml ./libs/ingest/
COPY libs/storage/pyproject.toml ./libs/storage/
COPY libs/forecasting/pyproject.toml ./libs/forecasting/
COPY libs/anomaly/pyproject.toml ./libs/anomaly/
COPY services/ingest/pyproject.toml ./services/ingest/
COPY services/storage-consumer/pyproject.toml ./services/storage-consumer/
COPY services/inference/pyproject.toml ./services/inference/
COPY services/anomaly-detector/pyproject.toml ./services/anomaly-detector/

# Source — uv-workspace requires sources for editable installs
COPY libs ./libs
COPY services ./services

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package noether-svc-ingest || \
    uv sync --no-dev --package noether-svc-ingest

ENV PATH="/opt/venv/bin:${PATH}"

USER 1001:1001

ENTRYPOINT ["python", "-m", "noether_svc_ingest"]
