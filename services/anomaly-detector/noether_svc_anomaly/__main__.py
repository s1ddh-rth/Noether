"""Entrypoint for the anomaly-detector service."""

from __future__ import annotations

import asyncio
import contextlib
import signal

from noether_ingest.logging import configure
from noether_ingest.metrics import start_metrics_server
from noether_storage import StorageSettings

from noether_svc_anomaly.config import AnomalySettings
from noether_svc_anomaly.worker import run


def main() -> None:
    settings = AnomalySettings()
    storage_settings = StorageSettings()
    log = configure(settings.log_level, service="anomaly-detector")
    start_metrics_server(settings.metrics_port, service="anomaly-detector")

    loop = asyncio.new_event_loop()
    task = loop.create_task(run(settings, storage_settings, log))

    def _shutdown() -> None:
        log.info("anomaly.shutdown_signal")
        task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _shutdown)

    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
