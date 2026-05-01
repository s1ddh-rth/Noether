"""Entrypoint for the agent service."""

from __future__ import annotations

import uvicorn

from noether_svc_agent.config import AgentSettings


def main() -> None:
    settings = AgentSettings()
    uvicorn.run(
        "noether_svc_agent.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        access_log=False,
    )


if __name__ == "__main__":
    main()
