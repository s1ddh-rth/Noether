"""Entrypoint for the inference service."""

from __future__ import annotations

import uvicorn

from noether_svc_inference.config import InferenceSettings


def main() -> None:
    settings = InferenceSettings()
    uvicorn.run(
        "noether_svc_inference.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        access_log=False,
    )


if __name__ == "__main__":
    main()
