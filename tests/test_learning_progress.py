"""Integration test validating on-line learning via feedback endpoints."""

from __future__ import annotations

import os
import time
import uuid
from urllib.parse import urlparse

import pytest
import requests

BASE = os.getenv("SOMA_API_URL", "http://127.0.0.1:9797")
MEMORY_URL = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://127.0.0.1:9595")
REDIS_URL = os.getenv("SOMABRAIN_REDIS_URL", "redis://127.0.0.1:6379/0")


def _api_ready(base: str) -> bool:
    try:
        resp = requests.get(f"{base.rstrip('/')}/health", timeout=2)
        return resp.status_code == 200 and resp.json().get("ok", False)
    except Exception:
        return False


def _memory_ready(url: str) -> bool:
    try:
        resp = requests.get(f"{url.rstrip('/')}/health", timeout=2)
        return resp.status_code == 200 and resp.json().get("ok", False)
    except Exception:
        return False


def _redis_ready(url: str) -> bool:
    try:
        import redis

        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        client = redis.Redis(host=host, port=port, socket_connect_timeout=1)
        return bool(client.ping())
    except Exception:
        return False


# Adjust skip logic: bypass when SOMA_API_URL_LOCK_BYPASS is set.
if os.getenv("SOMA_API_URL_LOCK_BYPASS", "0") not in ("1", "true", "yes"):
    pytestmark = pytest.mark.skipif(
        not (
            _api_ready(BASE) and _memory_ready(MEMORY_URL) and _redis_ready(REDIS_URL)
        ),
        reason="Live stack (API/memory/redis) not reachable on localhost",
    )
else:
    # No skip – ensure the test runs.
    pytestmark = pytest.mark.skipif(False, reason="bypass enabled")


def _get_adaptation_state() -> dict | None:
    resp = requests.get(f"{BASE}/context/adaptation/state", timeout=5)
    if resp.status_code == 404:
        return None
    assert resp.status_code == 200, resp.text
    return resp.json()


def _remember_memory(coord: str | None = None) -> None:
    payload = {
        "coord": coord,
        "payload": {
            "task": "learning-suite",
            "content": "learning test memory",
            "phase": "bootstrap",
            "quality_score": 0.9,
        },
    }
    resp = requests.post(f"{BASE}/remember", json=payload, timeout=5)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") and body.get("success"), body


def _run_evaluate(session_id: str, query: str, headers: dict[str, str]) -> dict:
    resp = requests.post(
        f"{BASE}/context/evaluate",
        json={"session_id": session_id, "query": query, "top_k": 3},
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _submit_feedback(
    session_id: str, query: str, prompt: str, headers: dict[str, str]
) -> None:
    payload = {
        "session_id": session_id,
        "query": query,
        "prompt": prompt,
        "response_text": "ack",
        "utility": 0.9,
        "reward": 0.9,
    }
    resp = requests.post(
        f"{BASE}/context/feedback",
        json=payload,
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("accepted") and body.get("adaptation_applied"), body


@pytest.mark.learning
def test_learning_feedback_increases_adaptation_weights():
    before_state = _get_adaptation_state()
    session_id = f"lrn-{uuid.uuid4().hex[:24]}"
    headers = {"X-Model-Confidence": "8.5", "X-Session-ID": session_id}
    query = "measure my adaptation progress"

    _remember_memory()

    evaluation = _run_evaluate(session_id, query, headers)
    baseline_weights = list(evaluation.get("weights", []))
    baseline_history_len = len(evaluation.get("working_memory", []) or [])
    history_lengths = [baseline_history_len]

    iterations = 4
    for _ in range(iterations):
        prompt = evaluation["prompt"]
        _submit_feedback(session_id, query, prompt, headers)
        time.sleep(0.05)
        evaluation = _run_evaluate(session_id, query, headers)
        history_lengths.append(len(evaluation.get("working_memory", []) or []))

    after_state = _get_adaptation_state()

    if before_state is not None and after_state is not None:
        alpha_before = before_state["retrieval"]["alpha"]
        alpha_after = after_state["retrieval"]["alpha"]
        lambda_before = before_state["utility"]["lambda_"]
        lambda_after = after_state["utility"]["lambda_"]

        assert alpha_after > alpha_before, {
            "alpha_before": alpha_before,
            "alpha_after": alpha_after,
            "after_state": after_state,
        }
        assert lambda_after > lambda_before, {
            "lambda_before": lambda_before,
            "lambda_after": lambda_after,
            "after_state": after_state,
        }

        history_before = before_state.get("history_len", 0)
        history_after = after_state.get("history_len", 0)
        assert history_after >= history_before + iterations, {
            "history_before": history_before,
            "history_after": history_after,
            "iterations": iterations,
        }
    else:
        final_weights = list(evaluation.get("weights", []))
        if not baseline_weights or not final_weights:
            final_history_len = history_lengths[-1] if history_lengths else 0
            assert final_history_len >= baseline_history_len + iterations, {
                "baseline_history_len": baseline_history_len,
                "final_history_len": final_history_len,
                "history_lengths": history_lengths,
                "iterations": iterations,
            }
            assert history_lengths == sorted(history_lengths), {
                "history_lengths": history_lengths,
                "message": "working memory length should be non-decreasing",
            }
            return
        assert len(baseline_weights) == len(final_weights)
        assert any(
            abs(f - b) > 1e-6 for f, b in zip(final_weights, baseline_weights)
        ), {
            "baseline_weights": baseline_weights,
            "final_weights": final_weights,
        }
