"""Prometheus metrics for the agent service.

Three primitives the design's observability section calls for:

- `agent_chats_total{status}` — counter, one per /chat request.
  status ∈ {"ok", "error"}.
- `agent_chat_latency_ms` — histogram, request handler latency in ms
  with industrial-AI-relevant buckets (most of the cost is local LLM
  calls, so buckets are weighted toward the seconds range).
- `agent_tool_calls_total{tool}` — counter, one per tool actually
  dispatched in fan-out (post-router-filter). Lets dashboards show
  tool mix and detect regressions like "the router stopped picking
  RAG".

`prometheus_client.REGISTRY` is the default global registry; the
`/metrics` route exposes its current snapshot.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

CHATS_TOTAL = Counter(
    "agent_chats_total",
    "Total /chat requests handled by the agent service.",
    labelnames=("status",),
)

CHAT_LATENCY_MS = Histogram(
    "agent_chat_latency_ms",
    "End-to-end /chat handler latency in milliseconds.",
    # Local LLM calls dominate; buckets up to ~30s.
    buckets=(50, 100, 250, 500, 1000, 2000, 5000, 10000, 20000, 30000, 60000),
)

TOOL_CALLS_TOTAL = Counter(
    "agent_tool_calls_total",
    "Tool dispatches by name (post-router selection).",
    labelnames=("tool",),
)


def render_metrics() -> tuple[bytes, str]:
    """Return (body, content_type) for `/metrics`."""
    return generate_latest(), CONTENT_TYPE_LATEST
