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

# Pre-train the baseline LightGBM forecaster so the image is self-contained
# and `/forecast` is queryable as soon as the container is healthy.
RUN mkdir -p /app/models \
 && python -m noether_forecasting.training --tag XMEAS_1 --output /app/models/xmeas_1.lgbm \
 && python -m noether_forecasting.training --tag XMEAS_7 --output /app/models/xmeas_7.lgbm \
 && python -m noether_forecasting.training --tag XMEAS_13 --output /app/models/xmeas_13.lgbm

ENV PATH="/opt/venv/bin:${PATH}" \
    MODEL_DIR=/app/models

EXPOSE 8000
USER 1001:1001

ENTRYPOINT ["python", "-m", "noether_svc_inference"]
