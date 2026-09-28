"""Seam invariant (ARCHITECTURE-INVARIANTS §2): embedding dim is 768 everywhere.

MEM_EMBED_DIM (agent) == SOMABRAIN_EMBED_DIM (brain) == SOMA_VECTOR_DIM (SFM) == 768.
No component may invent a fallback dimension or fail open on mismatch.
"""
from __future__ import annotations

import re
from pathlib import Path

BRAIN_PKG = Path(__file__).resolve().parents[2] / "somabrain"
REPO = Path(__file__).resolve().parents[2]

# Patterns that invent or accept a foreign embedding dimension.
FOREIGN_DIM_PATTERNS = (
    r'getattr\(\s*settings\s*,\s*["\']EMBED_DIM["\']\s*,\s*256\s*\)',
    r'getattr\(\s*cfg\s*,\s*["\']embed_dim["\']\s*,\s*256\s*\)',
    r'embed_dim["\']\s*,\s*256\s*\)',
    r'dim\s*=\s*256\b',
    r'dim=256\b',
    r'dim\s*:\s*int\s*=\s*256\b',
)


def _read(rel: str) -> str:
    return (BRAIN_PKG / rel).read_text(encoding="utf-8")


def _forbidden_hits(rel: str) -> list[str]:
    src = _read(rel)
    return [p for p in FOREIGN_DIM_PATTERNS if re.search(p, src)]


class TestNoForeignDimFallbacks:
    def test_core_singletons_no_256_fallback(self):
        assert _forbidden_hits("bootstrap/core_singletons.py") == []

    def test_singletons_no_256_fallback(self):
        assert _forbidden_hits("bootstrap/singletons.py") == []

    def test_embeddings_no_256_fallback(self):
        assert _forbidden_hits("admin/core/embeddings.py") == []

    def test_context_factory_no_hardcoded_256(self):
        assert _forbidden_hits("context/factory.py") == []

    def test_settings_default_is_768(self):
        src = _read("settings/cognitive.py")
        assert re.search(r"SOMABRAIN_EMBED_DIM\s*=\s*env\.int\(\s*[\"']EMBED_DIM[\"']\s*,\s*default\s*=\s*768\s*\)", src)

    def test_env_example_is_768(self):
        src = (REPO / ".env.example").read_text(encoding="utf-8")
        assert "SOMABRAIN_MEMORY_EMBED_DIM=256" not in src
        assert re.search(r"^EMBED_DIM=768\s*$", src, re.M)

    def test_system_health_reports_real_dim(self):
        src = _read("api/endpoints/system_health.py")
        assert "MILVUS_EMBEDDING_DIM" not in src
        assert "SOMABRAIN_EMBED_DIM" in src

    def test_milvus_payload_helper_has_no_128_default(self):
        src = _read("memory/milvus_client.py")
        assert not re.search(r"dim\s*:\s*int\s*=\s*128\b", src)

    def test_brain_settings_iso_default_is_768(self):
        src = _read("brain_settings/models.py")
        assert not re.search(r"[\"']embed_dim[\"']\s*:\s*\{\s*[\"']v[\"']\s*:\s*256", src)


class TestResolveEmbedDim:
    """Wished-for API: one fail-closed resolver used by every dim consumer."""

    def test_returns_768_from_settings(self):
        from somabrain.embed_dim import resolve_embed_dim

        class _S:
            SOMABRAIN_EMBED_DIM = 768
            SOMABRAIN_EMBED_DIM_SEAM = 768

        assert resolve_embed_dim(_S) == 768

    def test_raises_when_setting_missing(self):
        from somabrain.embed_dim import resolve_embed_dim

        class _S:
            pass

        try:
            resolve_embed_dim(_S)
        except RuntimeError as exc:
            assert "SOMABRAIN_EMBED_DIM" in str(exc)
        else:
            raise AssertionError("expected RuntimeError for missing SOMABRAIN_EMBED_DIM")

    def test_raises_on_contract_mismatch(self):
        """Fail closed when the effective dim violates the configured seam contract."""
        from somabrain.embed_dim import resolve_embed_dim

        class _S:
            SOMABRAIN_EMBED_DIM = 256
            SOMABRAIN_EMBED_DIM_SEAM = 768

        try:
            resolve_embed_dim(_S)
        except RuntimeError as exc:
            assert "768" in str(exc)
        else:
            raise AssertionError("expected RuntimeError for dim != seam contract")

    def test_contract_mismatch_in_both_directions(self):
        from somabrain.embed_dim import resolve_embed_dim

        class _S:
            SOMABRAIN_EMBED_DIM = 768
            SOMABRAIN_EMBED_DIM_SEAM = 256

        try:
            resolve_embed_dim(_S)
        except RuntimeError as exc:
            assert "256" in str(exc) and "768" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when seam contract differs")

    def test_settings_default_declares_seam_contract(self):
        src = _read("settings/cognitive.py")
        assert re.search(
            r"SOMABRAIN_EMBED_DIM_SEAM\s*=\s*env\.int\(\s*[\"']EMBED_DIM_SEAM[\"']\s*,\s*default\s*=\s*768\s*\)",
            src,
        )

    def test_no_hardcoded_dim_constant_in_resolver(self):
        src = _read("embed_dim.py")
        assert not re.search(r"SEAM_EMBED_DIM\s*=\s*\d+", src), "dim must come from settings, not a code constant"
        assert "SOMABRAIN_EMBED_DIM_SEAM" in src


class TestClientPayloadContract:
    """The 768 seam only counts if vectors actually cross the HTTP boundary.

    Regression guard: the client used to rebuild the store body as
    {coord, payload, memory_type} only, silently dropping embedding/tenant,
    and sent search bodies without a query embedding (every memory then fell
    back to hash vectors).
    """

    def test_store_payload_includes_embedding_and_tenant(self):
        from somabrain.memory.client.transport import build_store_payload

        p = build_store_payload(
            coord="c1",
            payload=b"x",
            memory_type="episodic",
            embedding=[0.0] * 768,
            tenant_id="t1",
        )
        assert p["embedding"] == [0.0] * 768
        assert p["tenant_id"] == "t1"
        assert p["coord"] == "c1"
        assert p["memory_type"] == "episodic"

    def test_store_payload_omits_embedding_when_absent(self):
        from somabrain.memory.client.transport import build_store_payload

        p = build_store_payload(
            coord="c1", payload=b"x", memory_type="episodic",
            embedding=None, tenant_id="t1",
        )
        assert "embedding" not in p

    def test_store_payload_rejects_wrong_dim(self):
        from somabrain.memory.client.transport import build_store_payload

        try:
            build_store_payload(
                coord="c1", payload=b"x", memory_type="episodic",
                embedding=[0.0] * 256, tenant_id="t1",
            )
        except ValueError as exc:
            assert "768" in str(exc)
        else:
            raise AssertionError("expected ValueError for 256-dim embedding")

    def test_search_payload_includes_query_embedding(self):
        from somabrain.memory.client.transport import build_search_payload

        p = build_search_payload(query="hello", top_k=5, embedding=[0.1] * 768, tenant_id="t1")
        assert p["embedding"] == [0.1] * 768
        assert p["query"] == "hello"
        assert p["top_k"] == 5

    def test_remember_ingest_gates_dim(self):
        src = _read("api/endpoints/memory_remember.py")
        assert (
            "ensure_embedding_dim" in src
            or "check_embedding_dim" in src
            or "EmbeddingDimensionError" in src
        ), "remember ingest must enforce the 768 embedding contract"
