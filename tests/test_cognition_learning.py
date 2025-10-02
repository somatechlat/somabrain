"""Live cognition integration tests (no mocks, real infrastructure required).

These tests assert that the deployed SomaBrain stack persists memories,
records feedback events, and grows session context when interacting with the
real HTTP endpoints, memory service, and backing Postgres database.
"""

from __future__ import annotations

import os
import time
import uuid
from urllib.parse import urlparse, urlunparse

import psycopg
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


pytestmark = pytest.mark.skipif(
    not (_api_ready(BASE) and _memory_ready(MEMORY_URL) and _redis_ready(REDIS_URL)),
    reason="Live stack (API/memory/redis) not reachable on localhost",
)


def _session_id(prefix: str = "cog") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _headers(session_id: str) -> dict[str, str]:
    return {
        "X-Model-Confidence": "8.0",
        "X-Session-ID": session_id,
        "X-Tenant-ID": os.getenv("SOMABRAIN_DEFAULT_TENANT", "sandbox"),
    }


def _resolve_postgres_dsn() -> str:
    explicit = os.getenv("SOMABRAIN_TEST_POSTGRES_DSN")
    if explicit:
        return explicit

    base = os.getenv("SOMABRAIN_POSTGRES_DSN")
    local_host = os.getenv("SOMABRAIN_POSTGRES_LOCAL_HOST", "127.0.0.1")
    local_port = os.getenv("SOMABRAIN_POSTGRES_LOCAL_PORT", "55432")

    if base:
        parsed = urlparse(base)
        user = parsed.username or ""
        password = parsed.password or ""

        auth = user
        if password:
            auth = f"{user}:{password}"

        if auth:
            netloc = f"{auth}@{local_host}:{local_port}"
        else:
            netloc = f"{local_host}:{local_port}"

        return urlunparse(parsed._replace(netloc=netloc))

    return f"postgresql://somabrain:somabrain-dev-password@{local_host}:{local_port}/somabrain"


def _connect_postgres():
    dsn = _resolve_postgres_dsn()
    try:
        return psycopg.connect(dsn)
    except psycopg.OperationalError as exc:  # pragma: no cover - skip on infra issues
        pytest.skip(f"Postgres unreachable: {exc}")


def _remember(content: str) -> dict:
    payload = {
        "coord": None,
        "payload": {
            "task": "cognition-suite",
            "content": content,
            "phase": "context",
            "quality_score": 0.92,
        },
    }
    resp = requests.post(f"{BASE}/remember", json=payload, timeout=10)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") and body.get("success"), body
    return body


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
    session_id: str,
    query: str,
    prompt: str,
    headers: dict[str, str],
    *,
    utility: float = 0.9,
    reward: float = 0.8,
    metadata: dict | None = None,
) -> dict:
    payload = {
        "session_id": session_id,
        "query": query,
        "prompt": prompt,
        "response_text": f"ack-{uuid.uuid4().hex[:6]}",
        "utility": utility,
        "reward": reward,
        "metadata": metadata or {},
        "tenant_id": os.getenv("SOMABRAIN_DEFAULT_TENANT", "sandbox"),
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
    return body


def _recall_memory(top_k: int = 20) -> list[dict]:
    resp = requests.post(f"{MEMORY_URL}/recall", json={"top_k": top_k}, timeout=10)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    return body


@pytest.mark.learning
def test_cognition_memory_round_trip_live():
    health_before = requests.get(f"{MEMORY_URL}/health", timeout=5).json()
    baseline = int(health_before.get("items", 0))

    marker = f"memory-{uuid.uuid4().hex[:10]}"
    _remember(f"Cognitive trace {marker}")

    deadline = time.time() + 3.0
    while time.time() < deadline:
        health_after = requests.get(f"{MEMORY_URL}/health", timeout=5).json()
        if int(health_after.get("items", 0)) >= baseline + 1:
            break
        time.sleep(0.1)
    else:  # pragma: no cover - defensive guard
        pytest.fail(
            f"memory service item count did not increase (baseline={baseline}, health={health_after})"
        )

    recalled = _recall_memory(top_k=25)
    assert isinstance(recalled, list) and recalled, "memory recall returned no entries"


@pytest.mark.learning
def test_cognition_feedback_persists_to_postgres():
    session_id = _session_id("cog-db")
    headers = _headers(session_id)
    marker = uuid.uuid4().hex[:12]
    query = f"Summarize cognitive gains for {marker}"

    evaluation = _run_evaluate(session_id, query, headers)
    prompt = evaluation["prompt"]

    metadata = {"tokens": 42.5, "model": "cognition-suite"}
    _submit_feedback(session_id, query, prompt, headers, metadata=metadata)

    time.sleep(0.2)  # allow async persistence (if any) to complete

    with _connect_postgres() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT query, prompt, response_text, utility, reward
                FROM feedback_events
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            )
            row = cur.fetchone()
            assert row is not None, "feedback_events entry missing"
            db_query, db_prompt, response_text, utility, reward = row
            assert marker in db_query
            assert db_prompt == prompt
            assert response_text.startswith("ack-"), response_text
            assert pytest.approx(utility, rel=1e-6) == 0.9
            assert pytest.approx(reward or 0.0, rel=1e-6) == 0.8

            cur.execute(
                """
                SELECT tokens, model
                FROM token_usage
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            )
            token_row = cur.fetchone()
            assert token_row is not None, "token_usage entry missing"
            tokens, model = token_row
            assert pytest.approx(tokens, rel=1e-6) == metadata["tokens"]
            assert model == metadata["model"]


@pytest.mark.learning
def test_cognition_session_history_growth_live():
    session_id = _session_id("cog-hist")
    headers = _headers(session_id)
    marker = uuid.uuid4().hex[:10]
    query = f"Plan next cognitive step for {marker}"

    _remember(f"Seed cognition memory {marker}")

    history_lengths: list[int] = []
    iterations = 4

    for _ in range(iterations):
        evaluation = _run_evaluate(session_id, query, headers)
        wm = evaluation.get("working_memory") or []
        history_lengths.append(len(wm))
        prompt = evaluation["prompt"]
        metadata = {"tokens": 12.0, "model": "cognition-iter"}
        _submit_feedback(session_id, query, prompt, headers, metadata=metadata)
        time.sleep(0.05)

    assert history_lengths == sorted(history_lengths), {
        "history_lengths": history_lengths,
        "message": "working memory should grow monotonically",
    }
    assert history_lengths[-1] >= history_lengths[0] + iterations - 1, {
        "history_lengths": history_lengths,
        "iterations": iterations,
    }
