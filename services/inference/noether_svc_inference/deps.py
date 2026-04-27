"""FastAPI dependencies — model registry, settings, auth."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, Header, HTTPException, status
from noether_forecasting import LightGBMForecaster

from noether_svc_inference.config import InferenceSettings


@lru_cache(maxsize=1)
def get_settings() -> InferenceSettings:
    return InferenceSettings()


class ModelRegistry:
    """Lazy-loads forecasters from disk and caches them in memory.

    File layout: `<MODEL_DIR>/<tag-lower>.lgbm`. Tag matching is case-insensitive
    so `XMEAS_1`, `xmeas_1`, `Xmeas_1` all resolve to the same artifact.
    """

    def __init__(self, model_dir: Path) -> None:
        self._dir = model_dir
        self._cache: dict[str, LightGBMForecaster] = {}

    def known_tags(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted(p.stem.upper() for p in self._dir.glob("*.lgbm"))

    def get(self, tag: str) -> LightGBMForecaster:
        key = tag.upper()
        if key not in self._cache:
            path = self._dir / f"{key.lower()}.lgbm"
            if not path.exists():
                raise FileNotFoundError(f"no model artifact for tag {tag} at {path}")
            self._cache[key] = LightGBMForecaster.load(path)
        return self._cache[key]


@lru_cache(maxsize=1)
def get_registry() -> ModelRegistry:
    return ModelRegistry(get_settings().model_dir)


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: InferenceSettings = Depends(get_settings),
) -> None:
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid X-API-Key",
        )
