"""GET /metrics — Prometheus exposition format."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from noether_svc_agent.metrics import render_metrics

router = APIRouter(tags=["meta"])


@router.get("/metrics")
def metrics() -> Response:
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
