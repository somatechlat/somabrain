"""Integration test validating on-line learning via feedback endpoints."""

from __future__ import annotations

import time
import uuid
import warnings

import pytest
import requests

from somabrain.testing.test_targets import TargetConfig, list_test_targets, target_ids


_TARGETS = list_test_targets()
_TARGET_IDS = target_ids(_TARGETS)


@pytest.fixture(params=_TARGETS, ids=_TARGET_IDS)
def target(request: pytest.FixtureRequest) -> TargetConfig:
    cfg: TargetConfig = request.param
    ok, reasons = cfg.probe()
    if not ok:
        tolerated: list[str] = []
        blocking: list[str] = []
        for reason in reasons:
            if "Memory health check not OK" in reason:
                tolerated.append(reason)
            else:
                blocking.append(reason)
        if blocking:
            msg = "; ".join(blocking + tolerated) if tolerated else "; ".join(blocking)
            pytest.skip(f"{cfg.label} unavailable: {msg}")
        if tolerated:
            warnings.warn(
                f"Proceeding despite memory probe warnings: {'; '.join(tolerated)}",
                RuntimeWarning,
            )
    return cfg


def _headers(cfg: TargetConfig, session_id: str) -> dict[str, str]:
    headers = {"X-Model-Confidence": "8.5", "X-Session-ID": session_id}
    if cfg.tenant:
        headers["X-Tenant-ID"] = cfg.tenant
    return headers


def _state_headers(cfg: TargetConfig) -> dict[str, str]:
    if not cfg.tenant:
        return {}
    return {"X-Tenant-ID": cfg.tenant}


def _get_adaptation_state(cfg: TargetConfig) -> dict | None:
    resp = requests.get(
        f"{cfg.api_base.rstrip('/')}/context/adaptation/state",
        headers=_state_headers(cfg),
        timeout=5,
    )
    if resp.status_code == 404:
        return None
    assert resp.status_code == 200, resp.text
    return resp.json()


def _remember_memory(
    cfg: TargetConfig, headers: dict[str, str], coord: str | None = None
) -> None:
    payload = {
        "coord": coord,
        "payload": {
            "task": "learning-suite",
            "content": "learning test memory",
            "phase": "bootstrap",
            "quality_score": 0.9,
        },
    }
    resp = requests.post(
        f"{cfg.api_base.rstrip('/')}/remember",
        json=payload,
        headers=headers,
        timeout=5,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") and body.get("success"), body


def _run_evaluate(
    cfg: TargetConfig, session_id: str, query: str, headers: dict[str, str]
) -> dict:
    resp = requests.post(
        f"{cfg.api_base.rstrip('/')}/context/evaluate",
        json={"session_id": session_id, "query": query, "top_k": 3},
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _submit_feedback(
    cfg: TargetConfig,
    session_id: str,
    query: str,
    prompt: str,
    headers: dict[str, str],
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
        f"{cfg.api_base.rstrip('/')}/context/feedback",
        json=payload,
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("accepted") and body.get("adaptation_applied"), body


@pytest.mark.learning
def test_learning_feedback_increases_adaptation_weights(target: TargetConfig):
    before_state = _get_adaptation_state(target)
    session_id = f"lrn-{uuid.uuid4().hex[:24]}"
    headers = _headers(target, session_id)
    query = "measure my adaptation progress"

    _remember_memory(target, headers)

    evaluation = _run_evaluate(target, session_id, query, headers)
    baseline_weights = list(evaluation.get("weights", []))
    baseline_history_len = len(evaluation.get("working_memory", []) or [])
    history_lengths = [baseline_history_len]

    iterations = 4
    expected_growth = max(1, iterations // 2)
    for _ in range(iterations):
        prompt = evaluation["prompt"]
        _submit_feedback(target, session_id, query, prompt, headers)
        time.sleep(0.05)
        evaluation = _run_evaluate(target, session_id, query, headers)
        history_lengths.append(len(evaluation.get("working_memory", []) or []))

    after_state = _get_adaptation_state(target)

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
        assert history_after >= history_before + expected_growth, {
            "history_before": history_before,
            "history_after": history_after,
            "iterations": iterations,
            "expected_growth": expected_growth,
        }
    else:
        final_weights = list(evaluation.get("weights", []))
        if not baseline_weights or not final_weights:
            final_history_len = history_lengths[-1] if history_lengths else 0
            assert final_history_len >= baseline_history_len + expected_growth, {
                "baseline_history_len": baseline_history_len,
                "final_history_len": final_history_len,
                "history_lengths": history_lengths,
                "iterations": iterations,
                "expected_growth": expected_growth,
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
