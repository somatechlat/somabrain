"""WAVE A fail-closed contracts — no soft-fallback, no outage dressed as [].

Covers:
* A3  predictor unknown provider refuses (no Mahalanobis fallback)
* A5  hybrid.py is gone (dead return-[] landmine)
* A6  utils.fetch_by_coord raises on outage / non-404; [] only on missing coord
* A7  SomaBrain has no direct Milvus write lane (milvus_ann deleted, T-1/B29)
* A12 remember_bulk per-item fallback raises listing failed indexes
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]


# ── A5 ──────────────────────────────────────────────────────────────────────


def test_hybrid_module_is_deleted():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("somabrain.memory.hybrid")


def test_no_production_module_imports_hybrid():
    hybrid_refs: list[str] = []
    for path in (BRAIN_ROOT / "somabrain").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "memory.hybrid" in text or "from .hybrid" in text or "hybrid_recall_sync" in text:
            hybrid_refs.append(str(path.relative_to(BRAIN_ROOT)))
    assert hybrid_refs == [], f"hybrid still referenced: {hybrid_refs}"


# ── A6 ──────────────────────────────────────────────────────────────────────


def _resp(status: int, json_data=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    return r


def test_fetch_by_coord_missing_client_raises():
    from somabrain.memory.utils import fetch_by_coord

    with pytest.raises(RuntimeError, match="MEMORY SERVICE REQUIRED"):
        fetch_by_coord(None, (0.0, 0.0, 0.0))


def test_fetch_by_coord_404_is_successful_empty():
    from somabrain.memory.utils import fetch_by_coord

    client = MagicMock()
    client.get.return_value = _resp(404)
    assert fetch_by_coord(client, (1.0, 2.0, 3.0)) == []


def test_fetch_by_coord_503_raises_not_empty():
    from somabrain.memory.utils import fetch_by_coord

    client = MagicMock()
    client.get.return_value = _resp(503)
    with pytest.raises(RuntimeError, match="HTTP 503"):
        fetch_by_coord(client, (1.0, 2.0, 3.0))


def test_fetch_by_coord_transport_error_raises():
    from somabrain.memory.utils import fetch_by_coord

    client = MagicMock()
    client.get.side_effect = OSError("connection reset")
    with pytest.raises(RuntimeError, match="unreachable"):
        fetch_by_coord(client, (1.0, 2.0, 3.0))


# ── A7 ──────────────────────────────────────────────────────────────────────


def test_no_direct_milvus_write_lane_in_somabrain():
    # T-1 / B29: Milvus is written only by SFM. SomaBrain must not ship a
    # direct pymilvus write module or a factory that builds one.
    assert not (BRAIN_ROOT / "somabrain" / "services" / "milvus_ann.py").exists()
    src = (BRAIN_ROOT / "somabrain" / "services" / "ann.py").read_text(
        encoding="utf-8"
    )
    assert "milvus_ann" not in src
    assert "MilvusAnnIndex" not in src
    assert "Milvus backend is forbidden" in src


# ── A12 ─────────────────────────────────────────────────────────────────────


def test_remember_bulk_partial_fallback_raises():
    from somabrain.memory import remember_bulk as rb

    prepared = [{"body": {"text": "a"}}, {"body": {"text": "b"}}]
    coords: list = [None, None]
    headers = {"X-Request-ID": "rid"}

    def store_http_sync_fn(body, hdrs):
        # first item ok, second fails
        if body.get("text") == "a":
            return True, {"memory": {"coordinate": [1.0, 1.0, 1.0]}}
        return False, None

    def extract(resp, idempotency_key=None):
        return (1.0, 1.0, 1.0)

    # Drive the 404/405 branch logic by calling the function with a bulk
    # endpoint that answers 405 and a store that fails item 1.
    def store_bulk_http_sync_fn(payload, hdrs):
        return False, 405, None

    def process_bulk_response_fn(response, prepared, coords, rid):
        raise AssertionError("should not reach process on 405")

    def prepare_bulk_items_fn(cfg, records):
        return prepared, ["real", "real"], coords, "t", "ns"

    def require_healthy_fn():
        return None

    monkey_extract = extract

    # Patch _extract_memory_coord used inside remember_bulk
    original = getattr(rb, "_extract_memory_coord", None)
    rb._extract_memory_coord = monkey_extract
    try:
        with pytest.raises(RuntimeError, match=r"indexes \[1\]"):
            rb.remember_bulk_sync(
                cfg=SimpleNamespace(),
                items=[("k", {"text": "a"}), ("k2", {"text": "b"})],
                request_id="rid",
                require_healthy_fn=require_healthy_fn,
                store_bulk_http_sync_fn=store_bulk_http_sync_fn,
                store_http_sync_fn=store_http_sync_fn,
                prepare_bulk_items_fn=prepare_bulk_items_fn,
                process_bulk_response_fn=process_bulk_response_fn,
                has_transport=True,
            )
    finally:
        if original is not None:
            rb._extract_memory_coord = original
        else:
            delattr(rb, "_extract_memory_coord")


# ── A3 (source-level, no settings boot) ────────────────────────────────────


def test_predictor_factory_has_no_soft_fallback():
    src = (BRAIN_ROOT / "somabrain" / "bootstrap" / "singletons.py").read_text(
        encoding="utf-8"
    )
    assert "falling back to mahalanobis" not in src
    assert "Unknown predictor provider" in src
    assert "SOMABRAIN_PREDICTOR_PROVIDER=mahal" in src


# ── A11 embed provider ─────────────────────────────────────────────────────


def test_embedder_has_no_tiny_fallback_and_no_fake_fde():
    src = (BRAIN_ROOT / "somabrain" / "admin" / "core" / "embeddings.py").read_text(
        encoding="utf-8"
    )
    assert "Falls back to 'tiny'" not in src
    assert "provider == \"fde\"" not in src
    assert "plabel = \"fde\"" not in src
    assert "Unknown embed provider" in src


# ── A8/A9/M5 remember client path ──────────────────────────────────────────


def test_record_to_outbox_handles_integrity_error_idempotent():
    src = (BRAIN_ROOT / "somabrain" / "memory" / "remember.py").read_text(
        encoding="utf-8"
    )
    assert "except IntegrityError:" in src
    assert "idempotency collision" in src
    assert "get_event_by_dedupe_key" in src


def test_aremember_background_never_silent_returns():
    src = (BRAIN_ROOT / "somabrain" / "memory" / "remember.py").read_text(
        encoding="utf-8"
    )
    # The silent return must be gone; missing transport must raise.
    assert "HTTP memory service required for background persistence" in src
    # Ensure the old silent pattern is not still present
    assert "if transport is None or transport.async_client is None:\n        return" not in src


def test_mark_outbox_sent_failure_is_warning_not_debug():
    src = (BRAIN_ROOT / "somabrain" / "memory" / "remember.py").read_text(
        encoding="utf-8"
    )
    assert "Failed to mark outbox event" in src
    # failure log must be warning (ops-visible), not debug
    assert "logger.warning(" in src
    assert "logger.debug(f\"Failed to mark outbox event sent" not in src


def test_payloads_for_coords_fail_closed():
    src = (BRAIN_ROOT / "somabrain" / "memory" / "client" / "read.py").read_text(
        encoding="utf-8"
    )
    assert "MEMORY SERVICE REQUIRED" in src
    assert "memory service unreachable (payloads_for_coords)" in src
    # old silent swallow of missing HTTP must be gone
    assert "return empty if no HTTP" not in src


# ── A4 / R6 operator batch ─────────────────────────────────────────────────


def test_production_sparsity_has_no_env_default():
    src = (BRAIN_ROOT / "somabrain" / "math" / "contracts.py").read_text(
        encoding="utf-8"
    )
    assert "os.environ.get(\"SOMABRAIN_BHDC_SPARSITY\"" not in src
    assert "require_setting(\"SOMABRAIN_BHDC_SPARSITY\")" in src


def test_sfm_tenant_defaults_removed():
    sfm = (
        Path("/Users/macbookpro201916i964gb1tb/Documents/GitHub/somafractalmemory")
        / "somafractalmemory"
        / "admin"
        / "core"
        / "services.py"
    ).read_text(encoding="utf-8")
    assert 'tenant: str = "default"' not in sfm
    assert "def _require_tenant" in sfm
    assert "tenant is required (T-5 fail-closed)" in sfm


def test_learning_path_tenant_defaults_removed():
    for rel in (
        "somabrain/services/learner_online.py",
        "somabrain/services/learner_dlq.py",
        "somabrain/learning/memory_events.py",
    ):
        src = (BRAIN_ROOT / rel).read_text(encoding="utf-8")
        assert 'or "default"' not in src, f"{rel} still has tenant default"
        assert "T-5 fail-closed" in src


# ── DEBT-008 Rust sole authority ───────────────────────────────────────────


def test_rust_is_sole_adaptation_math_authority():
    """Python AdaptationEngine must not twin the gain law (DEBT-008)."""
    engine_src = (BRAIN_ROOT / "somabrain" / "learning" / "adaptation" / "engine.py").read_text(
        encoding="utf-8"
    )
    # weight updates go through rust_math
    assert "apply_weight_updates_rust" in engine_src
    # no local gain-math twin
    assert "weight_delta(self._lr" not in engine_src
    rust_math = (
        BRAIN_ROOT / "somabrain" / "learning" / "adaptation" / "rust_math.py"
    ).read_text(encoding="utf-8")
    assert "somabrain_rs" in rust_math
    assert "Rust AdaptationEngine" in rust_math
    # rust module refuses without somabrain_rs
    assert "required for adaptation math" in rust_math


def test_rust_gains_match_contracts():
    rs = pytest.importorskip("somabrain_rs")
    from somabrain.math.contracts import ADAPT_GAINS

    eng = rs.AdaptationEngine(0.05)
    ga, gg, gl, gm, gn = eng.get_gains()
    assert ga == ADAPT_GAINS["alpha"]
    assert gg == ADAPT_GAINS["gamma"]
    assert gl == ADAPT_GAINS["lambda_"]
    assert gm == ADAPT_GAINS["mu"]
    assert gn == ADAPT_GAINS["nu"]


def test_rust_engine_bridge_has_no_default_tenant():
    src = (BRAIN_ROOT / "somabrain" / "learning" / "rust_engine.py").read_text(
        encoding="utf-8"
    )
    assert 'tenant_id: str = "default"' not in src
    assert "T-5 fail-closed" in src


# ── R5 one transport / one auth builder ─────────────────────────────────────


def test_one_sfm_auth_header_builder():
    src = (
        BRAIN_ROOT / "somabrain" / "memory" / "sfm_auth.py"
    ).read_text(encoding="utf-8")
    assert "def build_sfm_request_headers" in src
    # both transport surfaces must call the one builder
    for rel in (
        "somabrain/memory/transport.py",
        "somabrain/memory/client/transport.py",
    ):
        text = (BRAIN_ROOT / rel).read_text(encoding="utf-8")
        assert "build_sfm_request_headers" in text, rel
        # no second Authorization construction
        assert 'headers["Authorization"] = f"Bearer' not in text, rel


# ── ZERO optional paths (operator law) ─────────────────────────────────────


def test_zero_optional_paths_in_settings_resolve():
    src = (BRAIN_ROOT / "somabrain" / "settings" / "resolve.py").read_text(
        encoding="utf-8"
    )
    assert "def optional_setting" not in src
    assert "def optional_url" not in src
    assert "optional_setting" not in src
    assert "optional_url" not in src


def test_zero_optional_seams_in_memory_and_controls():
    for rel in (
        "somabrain/controls/memory_client.py",
        "somabrain/settings/managed.py",
        "somabrain/memory/sfm_auth.py",
        "somabrain/memory/transport.py",
        "somabrain/memory/client/transport.py",
    ):
        src = (BRAIN_ROOT / rel).read_text(encoding="utf-8")
        assert "optional_setting" not in src, rel
        assert "optional_url" not in src, rel


def test_memory_client_http_only_no_direct_mode():
    src = (BRAIN_ROOT / "somabrain" / "controls" / "memory_client.py").read_text(
        encoding="utf-8"
    )
    assert "_init_direct_mode" not in src
    assert 'mode == "direct"' not in src
    assert "require_setting(\"SOMA_API_TOKEN\")" in src
