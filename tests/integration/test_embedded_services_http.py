import os
import pytest
import requests


def _get_api_base() -> str:
    return (
        os.getenv("SOMABRAIN_API_URL")
        or os.getenv("SOMA_API_URL")
        or f"http://127.0.0.1:{os.getenv('SOMABRAIN_HOST_PORT', '9696')}"
    ).rstrip("/")


@pytest.mark.integration
def test_reward_health_embedded() -> None:
    base = _get_api_base()
    url = f"{base}/reward/health"
    try:
        r = requests.get(url, timeout=3)
    except Exception as exc:
        pytest.skip(f"Embedded reward not reachable: {exc}")
    if r.status_code == 404:
        pytest.skip("Embedded reward endpoint not mounted (non-dev mode)")
    if r.status_code == 403:
        pytest.skip("Embedded reward endpoint forbidden (likely non-dev mode)")
    r.raise_for_status()
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    assert body.get("ok") is True


@pytest.mark.integration
def test_learner_health_embedded() -> None:
    base = _get_api_base()
    url = f"{base}/learner/health"
    try:
        r = requests.get(url, timeout=3)
    except Exception as exc:
        pytest.skip(f"Embedded learner not reachable: {exc}")
    if r.status_code == 404:
        pytest.skip("Embedded learner endpoint not mounted (non-dev mode)")
    if r.status_code == 403:
        pytest.skip("Embedded learner endpoint forbidden (likely non-dev mode)")
    r.raise_for_status()
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    assert body.get("ok") is True
