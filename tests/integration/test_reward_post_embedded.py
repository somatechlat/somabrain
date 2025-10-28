import os
import time
import pytest
import requests


def _api() -> str:
    return (
        os.getenv("SOMABRAIN_API_URL")
        or os.getenv("SOMA_API_URL")
        or f"http://127.0.0.1:{os.getenv('SOMABRAIN_HOST_PORT', '9999')}"
    ).rstrip("/")


@pytest.mark.integration
def test_post_reward_embedded() -> None:
    base = _api()
    frame_id = f"test-{int(time.time()*1000)}"
    # Embedded reward producer is mounted under /reward, and defines POST /reward/{frame_id}
    # Therefore the full path is /reward/reward/{frame_id}
    url = f"{base}/reward/reward/{frame_id}"
    payload = {"r_task": 0.8, "r_user": 0.9, "r_latency": 0.1, "r_safety": 0.95, "r_cost": 0.05}
    try:
        r = requests.post(url, json=payload, timeout=5)
    except Exception as exc:
        pytest.skip(f"Embedded reward POST not reachable: {exc}")
    if r.status_code == 404:
        pytest.skip("Embedded reward endpoint not mounted (non-dev mode)")
    if r.status_code == 503:
        pytest.skip("Reward producer unavailable (Kafka not ready)")
    if r.status_code == 403:
        pytest.skip("Embedded reward endpoint forbidden (likely non-dev mode)")
    r.raise_for_status()
    body = r.json()
    assert body.get("status") == "ok"
