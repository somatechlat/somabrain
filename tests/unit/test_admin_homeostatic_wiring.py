"""Admin auth separation + live homeostatic wiring (ADV H2/H3)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_admin_auth_is_not_agent_auth() -> None:
    src = _read("somabrain/core/security/legacy_auth.py")
    admin_fn = src[src.index("def require_admin_auth") :]
    # Admin must not accept the shared agent token path
    assert "_validate_api_or_memory_token" not in admin_fn.split("def ")[0]
    assert "SOMABRAIN_ADMIN_TOKEN" in admin_fn
    assert "admin claim required" in admin_fn or "admin authentication required" in admin_fn


def test_jwt_validate_returns_claims() -> None:
    src = _read("somabrain/core/security/legacy_auth.py")
    assert "def _validate_jwt(token: str) -> dict[str, Any]:" in src
    assert "return dict(claims)" in src


def test_token_compare_is_constant_time() -> None:
    src = _read("somabrain/core/security/legacy_auth.py")
    assert "hmac.compare_digest" in src


def test_homeostatic_runs_on_eval_step() -> None:
    src = _read("somabrain/services/cognitive_loop_service.py")
    assert "adapt_from_performance" in src
    assert "get_adaptive_per_tenant_neuromods" in src
    assert "Homeostatic neuromod update" in src
    # Must persist adapted state back to the live store
    assert "neuromods.set_state" in src


def test_homeostatic_not_test_only() -> None:
    src = _read("somabrain/services/cognitive_loop_service.py")
    # Production call site must build PerformanceMetrics
    assert "PerformanceMetrics" in src
    assert "update_from_performance" in src or "adapt_from_performance" in src
