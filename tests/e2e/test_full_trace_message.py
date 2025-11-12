from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import requests


def _api_base() -> str:
    return (
        os.getenv("SOMABRAIN_API_URL")
        or "http://127.0.0.1:9696"
    ).rstrip("/")


def _auth_headers() -> Dict[str, str]:
    token = (
        os.getenv("SOMABRAIN_API_TOKEN")
        or os.getenv("API_TOKEN")
        or os.getenv("SOMABRAIN_JWT_SECRET")
    )
    return {"Authorization": f"Bearer {token}"} if token else {}


def _memory_endpoint_and_token() -> tuple[Optional[str], Optional[str]]:
    ep = (
        os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        or os.getenv("SOMABRAIN_HTTP_ENDPOINT")
        or os.getenv("MEMORY_SERVICE_URL")
    )
    tok = os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN")
    return ep, tok


def _write_artifact(base_dir: Path, name: str, data: Any) -> None:
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        p = base_dir / name
        if isinstance(data, (dict, list)):
            p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        elif isinstance(data, str):
            p.write_text(data, encoding="utf-8")
        else:
            p.write_text(repr(data), encoding="utf-8")
    except Exception:
        pass


def _safe_get(url: str, timeout: float = 5.0, headers: Optional[Dict[str, str]] = None):
    try:
        r = requests.get(url, timeout=timeout, headers=headers or {})
        if r.status_code in (401, 403) and not headers:
            r = requests.get(url, timeout=timeout, headers=_auth_headers())
        r.raise_for_status()
        return r
    except Exception:
        return None


def _safe_post(url: str, json_body: Dict[str, Any], timeout: float = 8.0, headers: Optional[Dict[str, str]] = None):
    try:
        r = requests.post(url, json=json_body, timeout=timeout, headers=headers or {})
        if r.status_code in (401, 403) and not headers:
            r = requests.post(url, json=json_body, timeout=timeout, headers=_auth_headers())
        r.raise_for_status()
        return r
    except Exception:
        return None


@pytest.mark.integration
@pytest.mark.benchmark
def test_full_trace_one_message(integration_env_ready) -> None:
    """
    True end-to-end trace of one message across the full brain pipeline.

    Artifacts written under artifacts/benchmarks/full_trace/<request_id>/
    include API transcripts, memory service responses, diagnostics, metrics.
    """

    base = _api_base()
    request_id = str(uuid.uuid4())
    trace_dir = Path.cwd() / "artifacts" / "benchmarks" / "full_trace" / request_id

    # 1) Health gate and diagnostics snapshot
    h = _safe_get(f"{base}/health", timeout=8.0)
    if h is None:
        pytest.skip("/health not reachable")
    health = h.json()
    _write_artifact(trace_dir, "01_health.json", health)
    assert health.get("ok") is True, health
    assert health.get("ready") is True, health

    d = _safe_get(f"{base}/diagnostics", timeout=5.0)
    if d is not None:
        _write_artifact(trace_dir, "02_diagnostics.json", d.json())

    # 2) Remember one message
    key_text = f"full-trace {int(time.time()*1000)}"
    remember_payload = {
        "coord": None,
        "payload": {
            "task": key_text,
            "importance": 1,
            "memory_type": "episodic",
            "trace_id": request_id,
        },
    }
    r = _safe_post(f"{base}/remember", remember_payload, headers={"X-Request-ID": request_id})
    assert r is not None, "remember failed"
    rj = r.json()
    _write_artifact(trace_dir, "03_remember_response.json", rj)
    assert rj.get("ok") and rj.get("success"), rj

    # 3) Poll recall for the same message
    from tests.utils.polling import wait_for

    def _has_recall() -> bool:
        rr = _safe_post(f"{base}/recall", {"query": key_text, "top_k": 3}, headers={"X-Request-ID": request_id})
        if rr is None:
            return False
        body = rr.json()
        # Collect candidates in common containers
        candidates = []
        for k in ("memory", "wm", "results", "items"):
            seq = body.get(k)
            if isinstance(seq, list):
                candidates += list(seq)
        for p in candidates:
            if isinstance(p, dict):
                t = str(p.get("task") or p.get("fact") or p.get("text") or "").lower()
                if t and (key_text.lower() in t or t in key_text.lower()):
                    _write_artifact(trace_dir, "04_recall_response.json", body)
                    return True
        return False

    wait_for(_has_recall, timeout=4.0, interval=0.15, desc="recall-visible")

    # 4) Memory service health + search confirmation
    mem_ep, mem_tok = _memory_endpoint_and_token()
    if mem_ep:
        mh = _safe_get(f"{mem_ep.rstrip('/')}/health", timeout=5.0, headers={"Authorization": f"Bearer {mem_tok}"} if mem_tok else None)
        if mh is not None:
            _write_artifact(trace_dir, "05_memory_health.json", mh.json() if mh.headers.get("content-type","" ).startswith("application/json") else mh.text)
        ms = _safe_post(
            f"{mem_ep.rstrip('/')}/memories/search",
            {"query": key_text, "top_k": 5},
            timeout=8.0,
            headers={"Authorization": f"Bearer {mem_tok}"} if mem_tok else None,
        )
        if ms is not None:
            _write_artifact(trace_dir, "06_memory_search.json", ms.json())

    # 5) Metrics snapshot (Prometheus text from /metrics)
    m = _safe_get(f"{base}/metrics", timeout=5.0)
    if m is not None:
        _write_artifact(trace_dir, "07_metrics.txt", m.text)

    # 6) Final health check with readiness summary
    h2 = _safe_get(f"{base}/health", timeout=5.0)
    assert h2 is not None
    health2 = h2.json()
    _write_artifact(trace_dir, "08_health_post.json", health2)
    assert health2.get("ok") is True and health2.get("ready") is True

    # 7) Assert core flags remain healthy (when present)
    for flag in ("memory_ok", "kafka_ok", "postgres_ok"):
        if flag in health2:
            assert health2[flag] is True, (flag, health2)
