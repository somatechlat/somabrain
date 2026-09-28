"""Round-trip proof for the canonical memory contract (THE SEAM) — live HTTP.

Replaces the previous in-process mock / monkeypatch suite (finding F-05
in SOMA-TRIAD-ARCH-001). Per ``somabrain/AGENT.md:138`` integration suites use
real infrastructure only. These tests exercise the running SomaBrain API at
``:30101`` end to end: remember → recall → forget, tenant isolation, and the
BrainBridge dialect.

Skips (never fakes) when the service is unreachable or the deployment token is
missing from the environment / ``.env``.

VIBE Rules: no mocks, no stubs, no synthesised credentials.
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

try:
    from dotenv import load_dotenv

    load_dotenv(".env", override=False)
except ImportError:  # pragma: no cover - dotenv is a project dependency
    pass

from tests.integration.infra_config import AUTH, URLS

BASE_URL = os.getenv(
    "SOMABRAIN_API_BASE", URLS.get("somabrain") or "http://127.0.0.1:30101"
)
# infra_config URLS has no somabrain key in older revisions; fall back explicitly.
if "somabrain" not in URLS:
    BASE_URL = os.getenv("SOMABRAIN_API_BASE", "http://127.0.0.1:30101")
else:
    BASE_URL = URLS["somabrain"]

TOKEN = AUTH.get("api_token") or os.getenv("SOMABRAIN_API_TOKEN") or ""

TIMEOUT = httpx.Timeout(10.0, connect=3.0)


def _auth_headers(tenant: str) -> dict:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Tenant-ID": tenant,
        "X-Request-ID": f"seam-{uuid.uuid4().hex[:12]}",
        "Content-Type": "application/json",
    }


def _service_available() -> bool:
    if not TOKEN:
        return False
    try:
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            resp = client.get("/health", headers={"Authorization": f"Bearer {TOKEN}"})
            return resp.status_code < 500
    except (httpx.HTTPError, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not _service_available(),
    reason="SomaBrain API not reachable at %s or SOMABRAIN_API_TOKEN missing"
    % BASE_URL,
)


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _post(client: httpx.Client, path: str, body: dict, tenant: str) -> httpx.Response:
    return client.post(path, json=body, headers=_auth_headers(tenant))


# ---------------------------------------------------------------------------
# Live seam assertions
# ---------------------------------------------------------------------------


def test_seam_remember_recall_roundtrip_returns_hit_with_score() -> None:
    """A seam-shaped remember must come back from recall with a score."""
    tenant = _unique("t-seam-roundtrip")
    text = f"the sky is blue on a clear day {uuid.uuid4().hex[:8]}"
    coord = "0.25,-0.5,0.75"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        write_body = {
            "text": text,
            "kind": "semantic",
            "tenant_id": tenant,
            "session_id": "sess-1",
            "coord": coord,
            "embedding": [0.1, 0.2, 0.3, 0.4],
            "salience": 0.8,
            "source": "agent-chat",
        }
        r = _post(client, "/memory/remember", write_body, tenant)
        assert r.status_code == 200, r.text
        ack = r.json()
        assert ack.get("ok") is True, ack
        assert str(ack.get("coord") or ack.get("coordinate")) == coord, ack

        # Read-your-writes: brief settle then recall.
        time.sleep(0.4)
        r2 = _post(
            client,
            "/memory/recall",
            {"query": "sky is blue", "k": 5, "tenant_id": tenant},
            tenant,
        )
        assert r2.status_code == 200, r2.text
        result = r2.json()
        hits = result.get("results") or []
        assert hits, f"recall returned nothing: {result}"
        top = hits[0]
        assert text in str(
            top.get("text") or top.get("payload", {}).get("text") or ""
        ), top
        assert top.get("score") is not None and float(top["score"]) > 0, top
        # MemoryHit shape / legacy aliases
        assert top.get("store") in (None, "somafractalmemory", "somabrain"), top
        assert top.get("coord") or top.get("coordinate"), top


def test_rich_write_shape_is_recalled_by_same_text() -> None:
    """The legacy rich shape writes the same representation recall reads."""
    tenant = _unique("t-rich")
    key = _unique("rich-key")
    task_text = f"quarterly revenue increased sharply {uuid.uuid4().hex[:8]}"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        write_body = {
            "tenant": tenant,
            "namespace": "test",
            "key": key,
            "value": {"task": task_text, "x": 1},
        }
        r = _post(client, "/memory/remember", write_body, tenant)
        assert r.status_code == 200, r.text
        ack = r.json()
        assert ack.get("ok") is True, ack

        time.sleep(0.4)
        r2 = _post(
            client,
            "/memory/recall",
            {
                "query": "revenue increased",
                "top_k": 5,
                "tenant": tenant,
                "namespace": "test",
            },
            tenant,
        )
        assert r2.status_code == 200, r2.text
        result = r2.json()
        texts = []
        for key_name in ("results", "memory", "wm", "ltm"):
            seq = result.get(key_name)
            if isinstance(seq, list):
                for h in seq:
                    if isinstance(h, dict):
                        texts.append(
                            str(
                                h.get("text")
                                or h.get("task")
                                or h.get("payload", {}).get("task")
                                or ""
                            )
                        )
        assert any(
            "quarterly revenue" in t or task_text[:20] in t for t in texts
        ), texts


def test_cross_tenant_recall_is_isolated() -> None:
    """A memory written by tenant A must not be visible to tenant B."""
    tenant_a = _unique("t-a")
    tenant_b = _unique("t-b")
    coord = "0.5,0.5,0.5"
    text = f"tenant A private note {uuid.uuid4().hex[:8]}"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = _post(
            client,
            "/memory/remember",
            {"text": text, "tenant_id": tenant_a, "coord": coord},
            tenant_a,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        time.sleep(0.3)
        r2 = _post(
            client,
            "/memory/recall",
            {"query": "private note", "tenant_id": tenant_b},
            tenant_b,
        )
        assert r2.status_code == 200, r2.text
        result = r2.json()
        hits = result.get("results") or []
        leaked = [
            h
            for h in hits
            if isinstance(h, dict)
            and text in str(h.get("text") or h.get("payload", {}) or "")
        ]
        assert not leaked, f"cross-tenant leak: {leaked}"


def test_forget_removes_the_memory() -> None:
    """forget must delete the stored item and report absence honestly."""
    tenant = _unique("t-forget")
    coord = "-0.1,0.2,-0.3"
    text = f"temporary scratch note {uuid.uuid4().hex[:8]}"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = _post(
            client,
            "/memory/remember",
            {"text": text, "tenant_id": tenant, "coord": coord},
            tenant,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        time.sleep(0.3)
        r_forget = _post(
            client, "/memory/forget", {"coord": coord, "tenant_id": tenant}, tenant
        )
        assert r_forget.status_code == 200, r_forget.text
        res = r_forget.json()
        assert res.get("ok") is True, res

        # Second forget reports absence rather than pretending to succeed.
        r2 = _post(
            client, "/memory/forget", {"coord": coord, "tenant_id": tenant}, tenant
        )
        assert r2.status_code in (200, 404), r2.text
        res2 = r2.json()
        assert res2.get("ok") is False, res2
        assert res2.get("error"), res2


def test_brainbridge_dialect_content_memory_type_metadata() -> None:
    """The BrainBridge ``/api/remember`` spelling and body shape must work.

    Body: ``{content, memory_type, metadata}`` with the tenant only in the
    ``X-Tenant-ID`` header — the exact shape used by
    ``tests/proofs/verify_brain_memory_bridge.py``.
    """
    tenant = _unique("public")
    content = f"Bridge verification test content {uuid.uuid4().hex[:8]}"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        write_body = {
            "content": content,
            "memory_type": "episodic",
            "metadata": {"origin": "bridge_verification"},
        }
        r = _post(client, "/api/remember", write_body, tenant)
        assert r.status_code == 200, r.text
        ack = r.json()
        assert ack.get("ok") is True, ack

        time.sleep(0.4)
        r2 = _post(
            client,
            "/api/recall",
            {"query": "Bridge verification", "k": 1, "memory_type": "episodic"},
            tenant,
        )
        assert r2.status_code == 200, r2.text
        result = r2.json()
        texts = []
        for key_name in ("results", "memory", "wm", "ltm"):
            seq = result.get(key_name)
            if isinstance(seq, list):
                for h in seq:
                    if isinstance(h, dict):
                        texts.append(
                            str(
                                h.get("text") or h.get("content") or h.get("task") or ""
                            )
                        )
        assert any(
            "Bridge verification" in t or content[:20] in t for t in texts
        ), texts


def test_write_without_tenant_is_rejected() -> None:
    """No silent default tenant: a write with no tenant anywhere is a 400."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        # No X-Tenant-ID header and no tenant in the body.
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "X-Request-ID": f"seam-{uuid.uuid4().hex[:12]}",
            "Content-Type": "application/json",
        }
        r = client.post(
            "/memory/remember", json={"text": "orphan note"}, headers=headers
        )
        assert r.status_code in (400, 401, 403), r.text


def test_explicit_coord_overrides_key_derivation() -> None:
    """An explicit coord is the storage identity even when a key is present."""
    tenant = _unique("t-coord")
    coord = "0.9,-0.9,0.1"

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        write_body = {
            "text": f"coord identity check {uuid.uuid4().hex[:8]}",
            "tenant_id": tenant,
            "key": _unique("some-key"),
            "coord": [0.9, -0.9, 0.1],
        }
        r = _post(client, "/memory/remember", write_body, tenant)
        assert r.status_code == 200, r.text
        ack = r.json()
        assert ack.get("ok") is True, ack
        returned = str(ack.get("coord") or ack.get("coordinate") or "")
        assert returned == coord or returned.startswith("[0.9"), ack
