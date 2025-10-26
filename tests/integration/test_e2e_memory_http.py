import time
from typing import Any, Dict, Iterable

import pytest
import requests

from somabrain.testing.test_targets import (
    list_test_targets,
    target_ids,
    TargetConfig,
)


def _post_json(url: str, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response from {url}: {r.text[:200]}")


@pytest.mark.integration
@pytest.mark.learning
@pytest.mark.parametrize("target", list_test_targets(), ids=target_ids(list_test_targets()))
class TestE2EMemoryHTTP:
    def test_health_backends_ok(self, target: TargetConfig) -> None:
        ok, reasons = target.probe()
        if not ok:
            pytest.skip("; ".join(reasons))

        url = f"{target.api_base.rstrip('/')}/health"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        body = resp.json()
        assert body.get("ok") is True, body
        # Be explicit about backend connectivity flags when present
        comps = body.get("components") or {}
        # If keys are missing (older schemas), don't fail the test on absent fields
        for key in ("kafka_ok", "postgres_ok", "memory_ok", "opa_ok"):
            if key in body:
                assert body[key] is True, body
            elif key in comps:
                assert bool(comps.get(key)) is True, body

    def test_remember_and_recall_end_to_end(self, target: TargetConfig) -> None:
        ok, reasons = target.probe()
        if not ok:
            pytest.skip("; ".join(reasons))

        base = target.api_base.rstrip("/")
        remember_url = f"{base}/remember"
        recall_url = f"{base}/recall"

        key_text = f"e2e memory test {int(time.time()*1000)}"
        payload: Dict[str, Any] = {
            "coord": None,
            "payload": {
                "task": key_text,
                "importance": 1,
                "memory_type": "episodic",
            },
        }

        rj = _post_json(remember_url, payload)
        assert rj.get("ok") and rj.get("success"), rj

        # Small backoff to allow WM admission on dev stacks
        time.sleep(0.4)

        body: Dict[str, Any] = {"query": key_text, "top_k": 5}
        r2 = _post_json(recall_url, body)

        # Search likely result containers in response
        candidates: Iterable[Any] = []
        for key in ("memory", "wm", "results", "items"):
            seq = r2.get(key)
            if isinstance(seq, list):
                candidates = list(candidates) + list(seq)

        text_lower = key_text.lower()
        found = False
        for p in candidates:
            if isinstance(p, dict):
                t = str(p.get("task") or p.get("fact") or p.get("text") or "").lower()
                if t and (text_lower in t or t in text_lower):
                    found = True
                    break

        assert found, f"Recall did not include the freshly stored memory. Response: {r2}"

    def test_remember_and_recall_five_memories(self, target: TargetConfig) -> None:
        ok, reasons = target.probe()
        if not ok:
            pytest.skip("; ".join(reasons))

        base = target.api_base.rstrip("/")
        remember_url = f"{base}/remember"
        recall_url = f"{base}/recall"

        keys: list[str] = []
        # Write five distinct memories
        for i in range(5):
            key_text = f"e2e batch memory {i} {int(time.time()*1000)}"
            payload: Dict[str, Any] = {
                "coord": None,
                "payload": {
                    "task": key_text,
                    "importance": 1,
                    "memory_type": "episodic",
                },
            }
            rj = _post_json(remember_url, payload)
            assert rj.get("ok") and rj.get("success"), rj
            keys.append(key_text)

        # Small backoff for WM admission across the batch
        time.sleep(0.6)

        # Verify each key is recallable individually
        for key_text in keys:
            body: Dict[str, Any] = {"query": key_text, "top_k": 5}
            r2 = _post_json(recall_url, body)
            candidates: Iterable[Any] = []
            for key in ("memory", "wm", "results", "items"):
                seq = r2.get(key)
                if isinstance(seq, list):
                    candidates = list(candidates) + list(seq)
            text_lower = key_text.lower()
            found = False
            for p in candidates:
                if isinstance(p, dict):
                    t = str(p.get("task") or p.get("fact") or p.get("text") or "").lower()
                    if t and (text_lower in t or t in text_lower):
                        found = True
                        break
            assert found, f"Recall missing for key '{key_text}'. Response: {r2}"

        # Emit a concise success summary (visible with `-s`)
        print("E2E 5-memory OK:", keys)
