"""FastAPI dependencies — model registry, settings, auth."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, Header, HTTPException, status
from noether_forecasting import EnsembleForecaster, LightGBMForecaster, PatchTSTForecaster

from noether_svc_inference.config import InferenceSettings

LoadedForecaster = LightGBMForecaster | PatchTSTForecaster | EnsembleForecaster


@lru_cache(maxsize=1)
def get_settings() -> InferenceSettings:
    return InferenceSettings()


# Extension → loader. Order is preference (ensemble wins over patchtst over lgbm).
_EXTENSION_LOADERS: list[tuple[str, type]] = [
    (".ensemble", EnsembleForecaster),
    (".patchtst", PatchTSTForecaster),
    (".lgbm", LightGBMForecaster),
]


class ModelRegistry:
    """Lazy-loads forecasters from disk and caches them in memory.

    File layout: `<MODEL_DIR>/<tag-lower>.{ensemble,patchtst,lgbm}`. When
    multiple kinds exist for the same tag, the highest-priority kind wins
    (ensemble > patchtst > lgbm). Tag matching is case-insensitive.
    """

    def __init__(self, model_dir: Path) -> None:
        self._dir = model_dir
        self._cache: dict[str, LoadedForecaster] = {}

    def known_tags(self) -> list[str]:
        if not self._dir.exists():
            return []
        tags: set[str] = set()
        for ext, _ in _EXTENSION_LOADERS:
            tags.update(p.stem.upper() for p in self._dir.glob(f"*{ext}"))
        return sorted(tags)

    def get(self, tag: str) -> LoadedForecaster:
        key = tag.upper()
        if key not in self._cache:
            for ext, loader in _EXTENSION_LOADERS:
                path = self._dir / f"{key.lower()}{ext}"
                if path.exists():
                    self._cache[key] = loader.load(path)
                    break
            else:
                raise FileNotFoundError(
                    f"no model artifact for tag {tag} under {self._dir} "
                    f"(looked for {[ext for ext, _ in _EXTENSION_LOADERS]})"
                )
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
