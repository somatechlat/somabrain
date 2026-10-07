"""Seam invariant (ARCHITECTURE-INVARIANTS §2): embedding dim is 768 everywhere.

MEM_EMBED_DIM (agent) == SOMABRAIN_EMBED_DIM (brain) == SOMA_VECTOR_DIM (SFM) == 768.
No component may invent a fallback dimension or fail open on mismatch.

Also carries the INVARIANTS §2.1 behavioural proof: a present precomputed
query vector forbids ``embed()`` on the live recall / re-rank path.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.no_django

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

    class _DimSettings:
        SOMABRAIN_EMBED_DIM = 768
        SOMABRAIN_EMBED_DIM_SEAM = 768

    def test_store_payload_includes_embedding_and_tenant(self):
        from somabrain.memory.client.transport import build_store_payload

        p = build_store_payload(
            coord="c1",
            payload=b"x",
            memory_type="episodic",
            embedding=[0.0] * 768,
            tenant_id="t1",
            settings=self._DimSettings,
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
                settings=self._DimSettings,
            )
        except ValueError as exc:
            assert "768" in str(exc)
        else:
            raise AssertionError("expected ValueError for 256-dim embedding")

    def test_search_payload_includes_query_embedding(self):
        from somabrain.memory.client.transport import build_search_payload

        p = build_search_payload(
            query="hello", top_k=5, embedding=[0.1] * 768, tenant_id="t1",
            settings=self._DimSettings,
        )
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

    def test_write_path_prefers_top_level_embedding(self):
        """INVARIANTS §5.5: top-level embedding wins; nested is fallback only."""
        src = _read("api/memory/models.py")
        assert "Prefer the first-class" in src or "prefer the first-class" in src.lower()
        # Nested value.embedding is lifted, not silently dropped.
        assert 'value.get("embedding")' in src
        assert 'd["embedding"] = list(emb)' in src


class _SpyEmbedder:
    """Records every ``embed`` call. Any call is a seam violation when a
    precomputed vector was supplied (INVARIANTS §2.1)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed(self, text: str):  # pragma: no cover - only reached on violation
        self.calls.append(str(text))
        return [0.0] * 8


class _RecordingScorer:
    """Captures the vectors handed to ``score`` so the test can prove the
    stored hit vector (not a text re-embed) is what gets scored."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any, Any, Any]] = []

    def score(self, query, candidate, *, age_seconds=None, cosine=None) -> float:
        self.calls.append((query, candidate, age_seconds, cosine))
        return 0.5


class _NoEmbedCfg:
    SOMABRAIN_WM_RECENCY_TIME_SCALE = 60.0
    SOMABRAIN_WM_RECENCY_MAX_STEPS = 1000.0
    SOMABRAIN_RECENCY_SHARPNESS = 1.2
    SOMABRAIN_RECENCY_FLOOR = 0.05
    SOMABRAIN_DENSITY_TARGET = 0.2
    SOMABRAIN_DENSITY_FLOOR = 0.6
    SOMABRAIN_DENSITY_WEIGHT = 0.35


class TestNoReembedWhenVectorPresent:
    """INVARIANTS §2.1 behavioural proof — no ``embed()`` when a vector is present.

    The previous guard was a source-grep that only proved the string
    ``embedder.embed`` sat on a branch; it never executed the path. These tests
    spy the embedder and call the real ranking / recall code.
    """

    def test_rescore_with_query_vec_never_calls_embed(self):
        from somabrain.memory.client.ranking import _rescore_and_rank_hits
        from somabrain.memory.client.types import RecallHit

        spy = _SpyEmbedder()
        scorer = _RecordingScorer()
        qvec = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        hit = RecallHit(
            payload={"text": "hello", "embedding": list(qvec)},
            score=0.9,
        )
        ranked = _rescore_and_rank_hits(
            _NoEmbedCfg(), scorer, spy, [hit], "hello", query_vec=qvec
        )
        assert spy.calls == [], "embed must NOT be called when query_vec is present"
        assert ranked, "hit must still be scored"

    def test_rescore_never_reembeds_stored_hit_text(self):
        from somabrain.memory.client.ranking import _rescore_and_rank_hits
        from somabrain.memory.client.types import RecallHit

        spy = _SpyEmbedder()
        scorer = _RecordingScorer()
        qvec = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        stored = [0.6, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        hit = RecallHit(
            payload={"text": "this text must never be embedded"},
            score=None,
            raw={"vector": list(stored)},
        )
        ranked = _rescore_and_rank_hits(
            _NoEmbedCfg(), scorer, spy, [hit], "query text", query_vec=qvec
        )
        assert spy.calls == [], "stored hit text must not be re-embedded"
        assert scorer.calls, "scorer must receive the stored vector"
        _q, candidate, _age, _cos = scorer.calls[0]
        assert list(candidate) == pytest.approx(stored)

    def test_scoring_uses_query_vec_and_stored_vector_cosine(self):
        from somabrain.admin.core.learning.scoring import UnifiedScorer
        from somabrain.memory.client.ranking import _rescore_and_rank_hits
        from somabrain.memory.client.types import RecallHit

        spy = _SpyEmbedder()
        scorer = UnifiedScorer(
            w_cosine=1.0,
            w_fd=0.0,
            w_recency=0.0,
            weight_min=0.0,
            weight_max=1.0,
            recency_scale=60.0,
            recency_sharpness=1.2,
            recency_floor=0.05,
            fd_backend=None,
        )
        qvec = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        aligned = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        orthogonal = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        hit_a = RecallHit(payload={"embedding": list(aligned)}, score=None)
        hit_b = RecallHit(payload={"embedding": list(orthogonal)}, score=None)
        ranked = _rescore_and_rank_hits(
            _NoEmbedCfg(), scorer, spy, [hit_a, hit_b], "q", query_vec=qvec
        )
        assert spy.calls == []
        assert ranked[0].score == pytest.approx(1.0, abs=1e-6)
        assert ranked[1].score == pytest.approx(0.0, abs=1e-6)

    def test_hit_without_vector_or_score_skips_hit_never_invents_score(self):
        """Neither stored vector nor store score → skip the hit, never a fake 0.0.

        One unscorable hit must not abort the batch (ADV H3). Score 0.0 would
        be a fabricated judgment the ranker then sorts on.
        """
        from somabrain.memory.client.ranking import _rescore_and_rank_hits
        from somabrain.memory.client.types import RecallHit

        spy = _SpyEmbedder()
        scorer = _RecordingScorer()
        qvec = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        bad = RecallHit(payload={"text": "no vector no score"}, score=None)
        good = RecallHit(
            payload={"text": "scored", "embedding": qvec}, score=None
        )
        ranked = _rescore_and_rank_hits(
            _NoEmbedCfg(), scorer, spy, [bad, good], "q", query_vec=qvec
        )
        assert spy.calls == [], "must not hash-embed text"
        assert all(h.payload.get("text") != "no vector no score" for h in ranked)
        assert any(h.payload.get("text") == "scored" for h in ranked)
        for h in ranked:
            assert h.score is None or (0.0 <= float(h.score) <= 1.0)

    def test_public_recall_with_embedding_skips_embed(self, monkeypatch):
        """Public path: ``recall(..., embedding=)`` must not reach ``embed``.

        This replaces the old source-grep that grepped for branch placement.
        """
        from somabrain.memory.client.read import ReadMixin
        from somabrain.memory.client.search import SearchMixin

        # Neutralise the seam dim gate so the stub can run without Django
        # settings; the vector length is irrelevant to the no-reembed proof.
        monkeypatch.setattr(
            "somabrain.memory.client.transport.ensure_embedding_dim",
            lambda embedding, **kwargs: embedding,
        )

        spy = _SpyEmbedder()
        scorer = _RecordingScorer()
        qvec = [0.1] * 8

        class _StubClient(ReadMixin, SearchMixin):
            def __init__(self) -> None:
                self.cfg = _NoEmbedCfg()
                self._scorer = scorer
                self._embedder = spy
                self._http = object()
                self._http_async = None
                self.last_body: dict = {}

            def _http_post_with_retries_sync(self, endpoint, body, headers):
                self.last_body = body
                return True, 200, {
                    "hits": [
                        {
                            "payload": {
                                "text": "stored text",
                                "universe": "real",
                                "embedding": list(qvec),
                            },
                            "score": 0.8,
                            "vector": list(qvec),
                        }
                    ]
                }

        client = _StubClient()
        hits = client.recall("query", top_k=1, universe="real", embedding=qvec)
        assert spy.calls == [], "public recall with embedding= must not call embed"
        assert hits, "recall must return scored hits"
        assert client.last_body.get("embedding") == pytest.approx(qvec)

    def test_public_arecall_with_embedding_skips_embed(self, monkeypatch):
        import asyncio

        from somabrain.memory.client.read import ReadMixin
        from somabrain.memory.client.search import SearchMixin

        monkeypatch.setattr(
            "somabrain.memory.client.transport.ensure_embedding_dim",
            lambda embedding, **kwargs: embedding,
        )

        spy = _SpyEmbedder()
        scorer = _RecordingScorer()
        qvec = [0.2] * 8

        class _StubAsyncClient(ReadMixin, SearchMixin):
            def __init__(self) -> None:
                self.cfg = _NoEmbedCfg()
                self._scorer = scorer
                self._embedder = spy
                self._http = object()
                self._http_async = object()

            async def _http_post_with_retries_async(self, endpoint, body, headers):
                return True, 200, {
                    "hits": [
                        {
                            "payload": {
                                "text": "stored text",
                                "universe": "real",
                                "embedding": list(qvec),
                            },
                            "score": 0.7,
                        }
                    ]
                }

        client = _StubAsyncClient()
        hits = asyncio.run(
            client.arecall("query", top_k=1, universe="real", embedding=qvec)
        )
        assert spy.calls == [], "public arecall with embedding= must not call embed"
        assert hits
