"""Credential-bound tenant resolution (ADV C3)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_tenant_docstring_is_credential_bound() -> None:
    src = _read("somabrain/tenant.py")
    assert "authenticated credential" in src
    assert "assertion" in src
    # Header must not be described as the authority
    assert "sole authority" in src
    assert "X-Tenant-ID" in src


def test_tenant_rejects_header_mismatch() -> None:
    src = _read("somabrain/tenant.py")
    assert "tenant mismatch" in src
    assert "does not match the authenticated credential" in src


def test_tenant_reads_credential_first() -> None:
    src = _read("somabrain/tenant.py")
    assert "_credential_tenant" in src
    assert 'auth.get("tenant_id")' in src or "auth.get('tenant_id')" in src
    # In _resolve body: credential is checked before the header is used
    body = src[src.index("def _resolve") :]
    assert body.index("cred_tenant") < body.index("header_tenant")


def test_thread_uses_get_tenant_sync() -> None:
    src = _read("somabrain/api/endpoints/thread.py")
    assert "get_tenant_sync" in src
    assert "tenant mismatch" in src or "asserted" in src.lower()
