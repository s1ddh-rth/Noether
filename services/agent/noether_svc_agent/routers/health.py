"""Liveness probe.

Readiness lands once we have backing dependencies to check (Ollama,
Neo4j, Postgres). For now the agent service has no startup-time
dependencies — keeping `/healthz` payload-free mirrors the inference
service's pattern.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
