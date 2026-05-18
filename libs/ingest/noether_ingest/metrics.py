"""Shared Prometheus exposition for the worker services.

Lives in ``noether_ingest`` for the same reason ``logging`` does: every
service depends on this lib transitively, so cross-cutting observability
plumbing belongs here rather than copy-pasted per service.

FastAPI services (inference, agent) expose ``/metrics`` via an in-app
route. The worker services (ingest, storage-consumer, anomaly-detector)
have no HTTP server of their own, so they call
:func:`start_metrics_server` to stand up a tiny side HTTP server that
Prometheus scrapes. The default global ``REGISTRY`` is used, so the
out-of-the-box ``process_*`` / ``python_*`` collectors are exported for
free alongside any service-specific metrics.
"""

from __future__ import annotations

import structlog
from prometheus_client import REGISTRY, Gauge, start_http_server

_SERVICE_INFO = Gauge(
    "noether_service_up",
    "Static 1 for a running Noether service; the `service` label "
    "lets a single Prometheus dashboard template across services.",
    labelnames=("service",),
)


def start_metrics_server(port: int, service: str) -> None:
    """Start the Prometheus exposition HTTP server for a worker.

    Binds ``0.0.0.0:<port>`` and serves the default registry at
    ``/metrics``. Safe to call once at service startup; raises
    ``OSError`` if the port is already bound (fail fast — a silent
    metrics outage is worse than a noisy boot failure).
    """
    log = structlog.get_logger().bind(service=service)
    start_http_server(port, registry=REGISTRY)
    _SERVICE_INFO.labels(service=service).set(1)
    log.info("metrics.server_started", port=port)
