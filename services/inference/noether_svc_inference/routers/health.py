"""Liveness + readiness."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from noether_svc_inference.deps import ModelRegistry, get_registry

router = APIRouter(tags=["meta"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(registry: ModelRegistry = Depends(get_registry)) -> dict[str, object]:
    return {"status": "ok", "models": registry.known_tags()}
