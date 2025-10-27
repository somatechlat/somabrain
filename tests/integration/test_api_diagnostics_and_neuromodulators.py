from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import pytest
import requests


def _get_api_base() -> str:
    return (
        os.getenv("SOMABRAIN_API_URL")
        or os.getenv("SOMA_API_URL")
        or f"http://127.0.0.1:{os.getenv('SOMABRAIN_HOST_PORT', '9696')}"
    ).rstrip("/")


def _auth_headers() -> Dict[str, str]:
    token = (
        os.getenv("SOMABRAIN_API_TOKEN")
        or os.getenv("API_TOKEN")
        or os.getenv("SOMABRAIN_JWT_SECRET")  # tolerate local JWT secret as a bearer in dev
    )
    return {"Authorization": f"Bearer {token}"} if token else {}


def _safe_get(url: str, timeout: float = 3.0, headers: Optional[Dict[str, str]] = None):
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout)
        if r.status_code in (401, 403):
            # Retry with potential auth header when first call had none
            if not headers:
                r = requests.get(url, headers=_auth_headers(), timeout=timeout)
        r.raise_for_status()
        return r
    except Exception:
        return None


def _safe_post(url: str, json: Dict[str, Any], timeout: float = 5.0, headers: Optional[Dict[str, str]] = None):
    try:
        r = requests.post(url, json=json, headers=headers or {}, timeout=timeout)
        if r.status_code in (401, 403):
            if not headers:
                r = requests.post(url, json=json, headers=_auth_headers(), timeout=timeout)
        r.raise_for_status()
        return r
    except Exception:
        return None


@pytest.mark.integration
def test_diagnostics_fields_present():
    base = _get_api_base()
    r = _safe_get(f"{base}/diagnostics")
    if r is None:
        pytest.skip("Diagnostics endpoint not reachable")
    body = r.json()
    # Minimal schema assertions (environment-independent)
    assert "external_backends_required" in body and isinstance(body["external_backends_required"], bool)
    assert "require_memory" in body and isinstance(body["require_memory"], bool)
    assert "memory_endpoint" in body and isinstance(body["memory_endpoint"], str)
    assert "api_version" in body and int(body["api_version"]) >= 1
    # Optional mode may be empty depending on environment; ensure key exists and is a string
    assert isinstance(body.get("mode", ""), str)


@pytest.mark.integration
def test_neuromodulators_roundtrip_and_learning_rate_effect():
    base = _get_api_base()

    # GET neuromodulators state
    r = _safe_get(f"{base}/neuromodulators")
    if r is None:
        pytest.skip("/neuromodulators GET not reachable")
    nm0 = r.json()
    for k in ("dopamine", "serotonin", "noradrenaline", "acetylcholine"):
        assert k in nm0

    # Reset adaptation to a known baseline (dev-only; skip LR check if forbidden)
    reset_allowed = True
    rr = _safe_post(f"{base}/context/adaptation/reset", {"base_lr": 0.05})
    if rr is None:
        # 403 or connection issues – continue but skip strict LR checks
        reset_allowed = False

    # Observe baseline learning rate
    rstate = _safe_get(f"{base}/context/adaptation/state")
    if rstate is None:
        pytest.skip("/context/adaptation/state not reachable")
    s0 = rstate.json()
    assert "learning_rate" in s0
    base_lr = float(s0.get("learning_rate") or 0.05)

    # Attempt to change dopamine via admin endpoint; if unauthorized, skip LR effect assertion
    headers = _auth_headers()
    rset = _safe_post(
        f"{base}/neuromodulators",
        {
            "dopamine": 0.8,
            "serotonin": float(nm0.get("serotonin", 0.1)),
            "noradrenaline": float(nm0.get("noradrenaline", 0.05)),
            "acetylcholine": float(nm0.get("acetylcholine", 0.05)),
        },
        headers=headers,
    )
    if rset is None:
        pytest.skip("/neuromodulators POST requires admin auth or is disabled; skipping LR effect check")

    # Apply a feedback event to force LR recomputation (dynamic LR uses dopamine)
    fb = _safe_post(
        f"{base}/context/feedback",
        {
            "session_id": "test-session",
            "query": "hello",
            "prompt": "p",
            "response_text": "r",
            "utility": 0.0,
        },
    )
    if fb is None:
        pytest.skip("/context/feedback not reachable; cannot validate LR effect")

    # Small settling time if persistence hooks are present
    time.sleep(0.1)

    rstate2 = _safe_get(f"{base}/context/adaptation/state")
    if rstate2 is None:
        pytest.skip("/context/adaptation/state second read failed")
    s1 = rstate2.json()
    assert "learning_rate" in s1

    # If we managed to reset, the expected LR with dopamine=0.8 is base_lr * 1.2 (capped)
    if reset_allowed:
        expected = 0.05 * 1.2
        assert abs(float(s1["learning_rate"]) - expected) < 1e-6
    else:
        # Without reset guarantees, at least assert LR changed or is within plausible dynamic range
        lr1 = float(s1["learning_rate"])
        assert 0.02 <= lr1 <= 0.07
