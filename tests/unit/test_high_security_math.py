"""Remaining HIGH fixes: Milvus tenant filter, universe fail-closed, top_k, wm_admit."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_milvus_tenant_expr_is_validated() -> None:
    src = _read("somabrain/memory/milvus_client.py")
    assert "re.fullmatch" in src
    assert "unsafe for a Milvus filter" in src


def test_universe_filter_fail_closed() -> None:
    src = _read("somabrain/memory/client/search.py")
    assert 'get("universe") or universe_value' not in src
    assert 'str((hit.payload or {}).get("universe")) == universe_value' in src


def test_top_k_clamped() -> None:
    src = _read("somabrain/api/endpoints/memory.py")
    assert "top_k: int = Field(10, ge=1, le=50" in src


def test_max_steps_clamped() -> None:
    src = _read("somabrain/schemas/api.py")
    assert "max_steps" in src
    assert "ge=1, le=50" in src


def test_wm_admit_fails_closed() -> None:
    src = _read("somabrain/services/cognitive_loop_service.py")
    assert "wm_admit = False" in src
    # Default must not be True
    assert "wm_admit = True" not in src
