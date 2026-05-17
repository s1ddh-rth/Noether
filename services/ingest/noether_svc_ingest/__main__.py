"""Entrypoint for the ingest service."""

from __future__ import annotations

import asyncio
import signal

from noether_ingest.logging import configure
from noether_ingest.metrics import start_metrics_server

from noether_svc_ingest.config import IngestSettings
from noether_svc_ingest.replayer import run


def main() -> None:
    settings = IngestSettings()
    log = configure(settings.log_level, service="ingest")
    start_metrics_server(settings.metrics_port, service="ingest")

    loop = asyncio.new_event_loop()
    task = loop.create_task(run(settings, log))

    def _shutdown() -> None:
        log.info("ingest.shutdown_signal")
        task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with __import__("contextlib").suppress(NotImplementedError):
            loop.add_signal_handler(sig, _shutdown)

    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
