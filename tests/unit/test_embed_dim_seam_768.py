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


class TestRecallAcceptsPrecomputedQueryVector:
    """The public recall surface must accept a precomputed query vector.

    INVARIANTS §2.1: the embedding is computed once, in the gateway, and sent
    precomputed. When present, the brain MUST NOT call embedder.embed — a
    store-side re-embed ranks a different vector space and recall is noise.

    These checks are source + resolver proofs so they run without booting the
    Django settings module (which requires the Vault-sourced
    SOMABRAIN_MEMORY_HTTP_TOKEN). A live round-trip is the integration gate.
    """

    def test_all_three_recall_models_carry_embedding(self):
        """Every public recall request model declares the first-class field.

        Pydantic v2 extra=ignore would silently drop an undeclared key — that
        is why each of the three surfaces must name it.
        """
        paths = [
            "api/endpoints/memory.py",
            "api/memory/models.py",
            "schemas/memory.py",
        ]
        for rel in paths:
            src = _read(rel)
            assert re.search(
                r"embedding:\s*list\[float\]\s*\|\s*None", src
            ), f"{rel} has no first-class embedding field (precomputed query vector)"

    def test_descriptions_forbid_reembed(self):
        for rel in ("api/endpoints/memory.py", "api/memory/models.py", "schemas/memory.py"):
            src = _read(rel)
            assert "MUST NEVER be re-embedded" in src, (
                f"{rel} does not state that a present vector is authoritative"
            )

    def test_wrong_dim_rejected(self):
        from somabrain.embed_dim import (
            EmbeddingDimensionError,
            ensure_embedding_dim,
            resolve_embed_dim,
        )

        class _S:
            SOMABRAIN_EMBED_DIM = 768
            SOMABRAIN_EMBED_DIM_SEAM = 768

        dim = resolve_embed_dim(_S)
        assert ensure_embedding_dim(None, settings=_S) is None
        bad = [0.0] * (dim + 1)
        try:
            ensure_embedding_dim(bad, settings=_S)
        except EmbeddingDimensionError as exc:
            assert str(dim) in str(exc)
        else:
            raise AssertionError("expected EmbeddingDimensionError for wrong dim")

    def test_validator_maps_dim_and_finite_to_400(self):
        recall_src = _read("api/memory/recall.py")
        assert "def _require_valid_query_vector" in recall_src
        assert "HttpError(400" in recall_src
        assert "ensure_embedding_dim" in recall_src
        assert "math.isfinite" in recall_src
        # The same validator backs the public /memory/recall handler.
        mem_src = _read("api/endpoints/memory.py")
        assert "_require_valid_query_vector" in mem_src

    def test_recall_handlers_never_reembed_when_vector_present(self):
        """Source proof: embedder.embed sits only on the degradation branch."""
        recall_src = _read("api/memory/recall.py")
        mem_src = _read("api/endpoints/memory.py")

        # The precomputed vector is what is forwarded to the store.
        assert "embedding=query_vec_list" in recall_src
        assert "embedding=query_vec" in mem_src
        assert "_arecall_ltm" in recall_src and "_arecall_ltm" in mem_src

        # embedder.embed is reached only when the caller omitted the vector.
        assert "if query_vec_list is not None:" in recall_src
        assert "if wm_vec is None:" in mem_src
        assert "recall.reembed" in recall_src
        assert "recall.reembed" in mem_src

    def test_write_path_prefers_top_level_embedding(self):
        """INVARIANTS §5.5: top-level embedding wins; nested is fallback only."""
        src = _read("api/memory/models.py")
        assert "Prefer the first-class" in src or "prefer the first-class" in src.lower()
        # Nested value.embedding is lifted, not silently dropped.
        assert 'value.get("embedding")' in src
        assert 'd["embedding"] = list(emb)' in src
