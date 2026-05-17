"""Entrypoint for the storage-consumer service."""

from __future__ import annotations

import asyncio
import contextlib
import signal

from noether_ingest.logging import configure as configure_logging
from noether_ingest.metrics import start_metrics_server
from noether_storage import StorageSettings

from noether_svc_storage.config import ConsumerSettings
from noether_svc_storage.consumer import run


def main() -> None:
    consumer_settings = ConsumerSettings()
    storage_settings = StorageSettings()
    log = configure_logging(consumer_settings.log_level, service="storage-consumer")
    start_metrics_server(consumer_settings.metrics_port, service="storage-consumer")

    loop = asyncio.new_event_loop()
    task = loop.create_task(run(consumer_settings, storage_settings, log))

    def _shutdown() -> None:
        log.info("storage_consumer.shutdown_signal")
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
