# syntax=docker/dockerfile:1.7
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl libpq5 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.6 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY libs/ingest/pyproject.toml ./libs/ingest/
COPY libs/storage/pyproject.toml ./libs/storage/
COPY libs/forecasting/pyproject.toml ./libs/forecasting/
COPY services/ingest/pyproject.toml ./services/ingest/
COPY services/storage-consumer/pyproject.toml ./services/storage-consumer/
COPY services/inference/pyproject.toml ./services/inference/

COPY libs ./libs
COPY services ./services
COPY eval ./eval

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package noether-svc-inference || \
    uv sync --no-dev --package noether-svc-inference

ENV PATH="/opt/venv/bin:${PATH}" \
    MODEL_DIR=/app/models

# Model artefacts are produced by the eval harness or by an explicit
# `python -m noether_forecasting.training` run. We don't bake them at build
# time because: (a) a 7-day synthetic panel + 3 LightGBM fits is slow, and
# (b) the eval harness is the authoritative M1 deliverable and trains its
# own models inline. /readyz will report models: [] until /forecast is hit
# against a tag whose artefact has been mounted into MODEL_DIR.
RUN mkdir -p /app/models

EXPOSE 8000
USER 1001:1001

ENTRYPOINT ["python", "-m", "noether_svc_inference"]
