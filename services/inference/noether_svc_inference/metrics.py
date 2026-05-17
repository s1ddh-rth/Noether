"""Prometheus metrics for the inference service.

Generic HTTP instrumentation (the service has several endpoints —
/forecast, /anomaly, /explain — so a per-request middleware is cleaner
than hand-rolled counters in each handler, unlike the agent service
which has a single /chat path):

- `inference_requests_total{method,path,status}` — counter.
- `inference_request_latency_ms{method,path}` — histogram. Forecast /
  anomaly inference is CPU-bound model work, so buckets run from sub-ms
  health checks up to multi-second cold model loads.

All inference endpoints use static paths (no path params), so labelling
by path is bounded-cardinality and safe.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS_TOTAL = Counter(
    "inference_requests_total",
    "Total HTTP requests handled by the inference service.",
    labelnames=("method", "path", "status"),
)

REQUEST_LATENCY_MS = Histogram(
    "inference_request_latency_ms",
    "HTTP request handler latency in milliseconds.",
    labelnames=("method", "path"),
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000),
)


def render_metrics() -> tuple[bytes, str]:
    """Return (body, content_type) for `/metrics`."""
    return generate_latest(), CONTENT_TYPE_LATEST
