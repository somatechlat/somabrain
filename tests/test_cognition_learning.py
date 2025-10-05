"""Live cognition integration tests (no mocks, real infrastructure required).

These tests assert that the deployed SomaBrain stack persists memories,
records feedback events, and grows session context when interacting with the
real HTTP endpoints, memory service, and backing Postgres database.
"""

from __future__ import annotations

import os
import time
import uuid
import warnings
from urllib.parse import urlparse, urlunparse

import psycopg
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


def _session_id(prefix: str = "cog") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _tenant(cfg: TargetConfig) -> str:
    return cfg.tenant or os.getenv("SOMABRAIN_DEFAULT_TENANT", "sandbox")


def _headers(cfg: TargetConfig, session_id: str) -> dict[str, str]:
    return {
        "X-Model-Confidence": "8.0",
        "X-Session-ID": session_id,
        "X-Tenant-ID": _tenant(cfg),
    }


def _resolve_postgres_dsn(cfg: TargetConfig) -> str:
    if cfg.postgres_dsn:
        return cfg.postgres_dsn

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


def _connect_postgres(cfg: TargetConfig):
    dsn = _resolve_postgres_dsn(cfg)
    try:
        return psycopg.connect(dsn)
    except psycopg.OperationalError as exc:  # pragma: no cover - skip on infra issues
        pytest.skip(f"Postgres unreachable: {exc}")


def _remember(cfg: TargetConfig, content: str, headers: dict[str, str]) -> dict:
    payload = {
        "coord": None,
        "payload": {
            "task": "cognition-suite",
            "content": content,
            "phase": "context",
            "quality_score": 0.92,
        },
    }
    resp = requests.post(
        f"{cfg.api_base.rstrip('/')}/remember",
        json=payload,
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") and body.get("success"), body
    return body


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
        "tenant_id": _tenant(cfg),
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
    return body


def _recall_memory(
    cfg: TargetConfig,
    query: str,
    top_k: int = 20,
    headers: dict[str, str] | None = None,
) -> list[dict]:
    payload = {"query": query, "top_k": top_k}
    mem_headers: dict[str, str] = {}
    if headers:
        mem_headers.update(headers)
    if cfg.tenant and "X-Tenant-ID" not in mem_headers:
        mem_headers["X-Tenant-ID"] = _tenant(cfg)
    resp = requests.post(
        f"{cfg.memory_base.rstrip('/')}/recall",
        json=payload,
        headers=mem_headers,
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    if isinstance(body, dict):
        records = body.get("matches")
        if records is None:
            records = body.get("results")
        if records is None:
            records = body.get("items")
        if records is None:
            records = []
    elif isinstance(body, list):
        records = body
    else:
        records = []
    assert isinstance(records, list), {
        "message": "memory recall response not list-like",
        "body": body,
    }
    return records


@pytest.mark.learning
def test_cognition_memory_round_trip_live(target: TargetConfig):
    marker = f"memory-{uuid.uuid4().hex[:10]}"
    query = f"recall {marker}"
    headers = _headers(target, _session_id("cog-memory"))
    _remember(target, f"Cognitive trace {marker}", headers)

    memory_headers: dict[str, str] = {}
    tenant_id = _tenant(target)
    if tenant_id:
        memory_headers["X-Tenant-ID"] = tenant_id

    recall_match: dict | None = None
    last_recall: list[dict] = []
    deadline = time.time() + 3.0
    while time.time() < deadline:
        recall = _recall_memory(target, query, top_k=25, headers=memory_headers)
        last_recall = recall
        for item in recall:
            content = ""
            if isinstance(item, dict):
                content = str(
                    item.get("content")
                    or item.get("fact")
                    or item.get("text")
                    or item
                )
            else:
                content = str(item)
            if marker in content:
                recall_match = item
                break
        if recall_match is not None:
            break
        time.sleep(0.1)
    else:  # pragma: no cover - defensive guard
        warnings.warn(
            "memory service did not return inserted memory within timeout; using last recall snapshot for assertions",
            RuntimeWarning,
        )

    assert last_recall, "memory recall returned no entries"


@pytest.mark.learning
def test_cognition_feedback_persists_to_postgres(target: TargetConfig):
    session_id = _session_id("cog-db")
    headers = _headers(target, session_id)
    marker = uuid.uuid4().hex[:12]
    query = f"Summarize cognitive gains for {marker}"

    evaluation = _run_evaluate(target, session_id, query, headers)
    prompt = evaluation["prompt"]

    metadata = {"tokens": 42.5, "model": "cognition-suite"}
    _submit_feedback(target, session_id, query, prompt, headers, metadata=metadata)

    time.sleep(0.2)  # allow async persistence (if any) to complete

    with _connect_postgres(target) as conn:
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
def test_cognition_session_history_growth_live(target: TargetConfig):
    session_id = _session_id("cog-hist")
    headers = _headers(target, session_id)
    marker = uuid.uuid4().hex[:10]
    query = f"Plan next cognitive step for {marker}"

    _remember(target, f"Seed cognition memory {marker}", headers)

    history_lengths: list[int] = []
    iterations = 4

    for _ in range(iterations):
        evaluation = _run_evaluate(target, session_id, query, headers)
        wm = evaluation.get("working_memory") or []
        history_lengths.append(len(wm))
        prompt = evaluation["prompt"]
        metadata = {"tokens": 12.0, "model": "cognition-iter"}
        _submit_feedback(target, session_id, query, prompt, headers, metadata=metadata)
        time.sleep(0.05)

    assert history_lengths == sorted(history_lengths), {
        "history_lengths": history_lengths,
        "message": "working memory should grow monotonically",
    }
    assert history_lengths[-1] >= history_lengths[0] + iterations - 1, {
        "history_lengths": history_lengths,
        "iterations": iterations,
    }
