"""Prometheus exposition + per-request instrumentation for inference."""

from __future__ import annotations

from fastapi.testclient import TestClient
from noether_svc_inference.app import build_app


def _counter(body: str, label_prefix: str) -> float:
    for line in body.splitlines():
        if line.startswith(label_prefix):
            return float(line.rsplit(maxsplit=1)[-1] if " " in line else "0")
    return 0.0


def test_metrics_endpoint_returns_prometheus_format() -> None:
    with TestClient(build_app()) as client:
        client.get("/healthz")  # produce one labelled observation
        resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "inference_requests_total" in body
    assert "# TYPE inference_request_latency_ms histogram" in body
    assert "inference_request_latency_ms_bucket" in body


def test_request_increments_counter_and_observes_latency() -> None:
    with TestClient(build_app()) as client:
        before = _counter(
            client.get("/metrics").text,
            'inference_requests_total{method="GET",path="/healthz",status="200"}',
        )

        assert client.get("/healthz").status_code == 200

        after = _counter(
            client.get("/metrics").text,
            'inference_requests_total{method="GET",path="/healthz",status="200"}',
        )

    assert after == before + 1
