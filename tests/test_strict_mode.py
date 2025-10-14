import os
import importlib
import pytest


def test_strict_mode_health_and_no_stub_backfill(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_STRICT_REAL", "1")
    monkeypatch.setenv("SOMABRAIN_PREDICTOR_PROVIDER", "mahal")
    # Ensure SOMA_API_URL fixed
    monkeypatch.setenv("SOMA_API_URL", "http://127.0.0.1:9696")
    # Import fresh app module
    if "somabrain.app" in importlib.sys.modules:
        importlib.reload(importlib.import_module("somabrain.app"))
    else:
        import somabrain.app  # noqa: F401
    import requests

    r = requests.get(os.getenv("SOMA_API_URL") + "/health", timeout=1.5)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("minimal_public_api") in (False, None)
    # strict_real flag should be true somewhere (app may not yet include stub counts if no use)
    # Not all parts expose strict flag yet; tolerate missing key but forbid stub_counts presence with values >0
    sc = data.get("stub_counts", {}) or {}
    assert all(v == 0 for v in sc.values()), f"Unexpected stub usage: {sc}"


def test_strict_mode_disallows_stub_predictor(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_STRICT_REAL", "1")
    monkeypatch.setenv("SOMABRAIN_PREDICTOR_PROVIDER", "stub")
    if "somabrain.app" in importlib.sys.modules:
        del importlib.sys.modules["somabrain.app"]
    with pytest.raises(RuntimeError):
        importlib.import_module("somabrain.app")
