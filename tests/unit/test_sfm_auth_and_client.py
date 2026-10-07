"""SFM bearer resolution and client base_url integrity."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

ROOT = Path(__file__).resolve().parents[2]


def test_sfm_token_single_resolver() -> None:
    src = (ROOT / "somabrain" / "memory" / "sfm_auth.py").read_text()
    assert "def resolve_sfm_api_token" in src
    assert "get_api_token" in src


def test_transports_use_resolver() -> None:
    for rel in (
        "somabrain/memory/transport.py",
        "somabrain/memory/client/transport.py",
    ):
        src = (ROOT / rel).read_text()
        assert "resolve_sfm_api_token" in src
        assert "fail closed" in src.lower() or "fail-closed" in src.lower() or "not provisioned" in src


def test_client_has_no_ports_json_hijack() -> None:
    src = (ROOT / "clients" / "python" / "somabrain_client" / "__init__.py").read_text()
    assert "_load_ports" not in src
    assert "SOMABRAIN_HOST_PORT" not in src
    assert 'base_url = f"http://localhost:' not in src
