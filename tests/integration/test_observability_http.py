from __future__ import annotations

import os
import pytest
import requests


def _get_port_candidates(name: str, alternatives: list[str]) -> list[str]:
    val = os.getenv(name)
    ports: list[str] = []
    if val and val.strip():
        ports.append(val.strip())
    for fb in alternatives:
        if fb not in ports:
            ports.append(fb)
    return ports


def _try_get(urls: list[str], timeout: float = 3.0) -> requests.Response | None:
    for url in urls:
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception:
            continue
    return None


@pytest.mark.integration
def test_prometheus_ready() -> None:
    ports = _get_port_candidates(
        "PROMETHEUS_HOST_PORT", ["30005", "30008"]
    )  # common mappings
    urls = [f"http://127.0.0.1:{p}/-/ready" for p in ports]
    r = _try_get(urls)
    if r is None:
        pytest.skip(f"Prometheus not reachable on {ports}")
    assert r.text.strip().lower().startswith("prometheus server is ready"), r.text[:80]


@pytest.mark.integration
def test_kafka_exporter_metrics_head() -> None:
    ports = _get_port_candidates(
        "KAFKA_EXPORTER_HOST_PORT", ["30003", "30004"]
    )  # common mappings
    urls = [f"http://127.0.0.1:{p}/metrics" for p in ports]
    r = _try_get(urls)
    if r is None:
        pytest.skip(f"Kafka exporter not reachable on {ports}")
    assert len(r.text) > 0


@pytest.mark.integration
def test_postgres_exporter_metrics_head() -> None:
    ports = _get_port_candidates(
        "POSTGRES_EXPORTER_HOST_PORT", ["30007"]
    )  # common mapping
    urls = [f"http://127.0.0.1:{p}/metrics" for p in ports]
    r = _try_get(urls)
    if r is None:
        pytest.skip(f"Postgres exporter not reachable on {ports}")
    assert len(r.text) > 0


@pytest.mark.integration
def test_opa_health() -> None:
    # Prefer standardized 30004, but tolerate 8181 as a legacy alternative
    ports = _get_port_candidates(
        "OPA_HOST_PORT", ["30004", "8181"]
    )  # host mapping (container is 8181)
    urls = []
    for p in ports:
        urls.append(f"http://127.0.0.1:{p}/health?plugins")
        urls.append(f"http://127.0.0.1:{p}/health")
    r = _try_get(urls)
    if r is None:
        pytest.skip(f"OPA not reachable on {ports}")
    # Minimal assertion: status already 200 via _try_get; body can be '{}' depending on OPA
    assert r.text is not None
