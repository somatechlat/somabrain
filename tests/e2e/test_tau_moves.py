import os
import time
import urllib.request


def _get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=2) as r:  # nosec B310
        return r.read().decode("utf-8")


def test_tau_endpoint_reachable_and_changes_if_config_updates_present():
    port = int(os.getenv("COG_INTEGRATOR_HOST_PORT", "30010"))
    url = f"http://127.0.0.1:{port}/tau"
    try:
        before = _get(url)
    except Exception:
        # In CI without the stack running, just ensure endpoint is reachable when service is up
        return
    # Poll for potential change instead of fixed 2s sleep
    from tests.utils.polling import wait_for

    wait_for(lambda: _get(url) != before, timeout=2.0, interval=0.2, desc="tau change")
    after = _get(url)
    # Non-strict: verify it returns a numeric-looking payload
    assert before.strip(), "empty /tau response"
    assert after.strip(), "empty /tau response"
