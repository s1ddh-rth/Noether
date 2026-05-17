import socket
import urllib.request

from noether_ingest.metrics import start_metrics_server


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_metrics_server_serves_default_registry() -> None:
    port = _free_port()
    start_metrics_server(port, service="unit-test")

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5) as resp:
        assert resp.status == 200
        body = resp.read().decode()

    # Service-up gauge with our label, plus the free process collectors.
    assert 'noether_service_up{service="unit-test"} 1.0' in body
    assert "python_info" in body
