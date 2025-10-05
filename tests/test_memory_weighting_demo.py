import pytest

from somabrain.memory_client import MemoryClient
from somabrain.config import Config


class DummyEmbedder:
    def embed(self, text: str):
        # Very naive deterministic vector: map chars to positions
        import numpy as np

        v = np.zeros(8, dtype=float)
        for ch in text.lower():
            idx = ord(ch) % 8
            v[idx] += 1.0
        n = (v**2).sum() ** 0.5
        if n > 0:
            v /= n
        return v.tolist()


@pytest.fixture(autouse=True)
def inject_embedder(monkeypatch):
    # Inject runtime.embedder expected by memory_client recall path using a real module object
    import types
    import sys
    import somabrain

    rt = types.ModuleType("somabrain.runtime")
    rt.embedder = DummyEmbedder()
    sys.modules["somabrain.runtime"] = rt  # type: ignore
    # Also attach as attribute so `from somabrain import runtime` works
    try:
        setattr(somabrain, "runtime", rt)
    except Exception:
        pass
    yield
    sys.modules.pop("somabrain.runtime", None)
    try:
        if hasattr(somabrain, "runtime"):
            delattr(somabrain, "runtime")
    except Exception:
        pass


@pytest.fixture
def client(monkeypatch):
    # Allow disabling hard memory requirement for this demo test
    monkeypatch.setenv("SOMABRAIN_REQUIRE_MEMORY", "0")
    # Ensure no HTTP endpoint so we exercise in-process deterministic recall path safely
    monkeypatch.setenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "")
    cfg = Config(namespace="demo:test")
    mc = MemoryClient(cfg)
    # Hard disable any accidental HTTP client created with empty base_url
    mc._http = None  # type: ignore[attr-defined]
    mc._http_async = None  # type: ignore[attr-defined]
    return mc


@pytest.mark.parametrize("enable_weighting", [False, True])
def test_weighting_effect(enable_weighting, client, monkeypatch):
    # Clear env flags
    monkeypatch.delenv("SOMABRAIN_MEMORY_ENABLE_WEIGHTING", raising=False)
    monkeypatch.delenv("SOMABRAIN_MEMORY_PHASE_PRIORS", raising=False)
    monkeypatch.delenv("SOMABRAIN_MEMORY_QUALITY_EXP", raising=False)

    if enable_weighting:
        monkeypatch.setenv("SOMABRAIN_MEMORY_ENABLE_WEIGHTING", "1")
        monkeypatch.setenv(
            "SOMABRAIN_MEMORY_PHASE_PRIORS",
            "bootstrap:1.1,general:1.0,specialized:1.05",
        )
        monkeypatch.setenv("SOMABRAIN_MEMORY_QUALITY_EXP", "1.0")

    # Insert three memories with similar text so base cosine is close
    client.remember(
        "m1", {"content": "alpha beta gamma", "phase": "general", "quality_score": 0.4}
    )
    client.remember(
        "m2",
        {"content": "alpha beta gamma", "phase": "bootstrap", "quality_score": 0.9},
    )
    client.remember(
        "m3",
        {"content": "alpha beta gamma", "phase": "specialized", "quality_score": 0.6},
    )

    hits = client.recall("alpha beta", top_k=3)
    order = [h.payload.get("phase") for h in hits]
    print(f"WEIGHTING_DEMO enable_weighting={enable_weighting} order={order}")
    if not enable_weighting:
        # Without weighting, ordering is purely cosine similarity; with identical content
        # insertion order should govern stable ordering (general, bootstrap, specialized)
        assert order[0] == "general"
    else:
        # With weighting, bootstrap has highest phase*quality (1.1 * 0.9)
        # specialized: 1.05 * 0.6, general: 1.0 * 0.4
        assert order[0] == "bootstrap"
        assert "general" in order and "specialized" in order
