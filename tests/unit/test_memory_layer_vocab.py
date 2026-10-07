"""One recall-layer vocabulary across every memory recall surface (ADV-3 C2).

``api/endpoints/memory.py`` (``/memory/recall``) and ``api/memory/recall.py``
(``/api/memory/recall``) used to disagree: one defaulted to ``"both"`` and the
other to ``"all"``, and a synonym that missed the other handler's accepted set
returned zero hits with 200. Both now share ``normalize_layer``.

Contract:
- ``wm`` / ``ltm`` / ``both`` are canonical.
- ``all`` is a synonym for ``both`` (legacy callers keep working).
- omitted / empty / ``None`` means both layers.
- any other value raises so the handler can 400 — a typo must never be a
  silent empty result set.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN = Path(__file__).resolve().parents[2] / "somabrain"


def _load_normalize_layer():
    """Import ``normalize_layer`` without Django settings."""
    from somabrain.api.memory.helpers import (
        LAYER_BOTH,
        LAYER_LTM,
        LAYER_WM,
        normalize_layer,
    )

    return normalize_layer, LAYER_WM, LAYER_LTM, LAYER_BOTH


class TestNormalizeLayer:
    def test_canonical_values_pass_through(self):
        normalize_layer, LAYER_WM, LAYER_LTM, LAYER_BOTH = _load_normalize_layer()
        assert normalize_layer("wm") == LAYER_WM
        assert normalize_layer("ltm") == LAYER_LTM
        assert normalize_layer("both") == LAYER_BOTH

    def test_all_is_synonym_for_both(self):
        normalize_layer, _WM, _LTM, LAYER_BOTH = _load_normalize_layer()
        assert normalize_layer("all") == LAYER_BOTH
        assert normalize_layer("ALL") == LAYER_BOTH
        assert normalize_layer(" All ") == LAYER_BOTH

    def test_case_and_whitespace_insensitive(self):
        normalize_layer, LAYER_WM, LAYER_LTM, _BOTH = _load_normalize_layer()
        assert normalize_layer(" WM ") == LAYER_WM
        assert normalize_layer("Ltm") == LAYER_LTM

    def test_omitted_means_both(self):
        normalize_layer, _WM, _LTM, LAYER_BOTH = _load_normalize_layer()
        assert normalize_layer(None) == LAYER_BOTH
        assert normalize_layer("") == LAYER_BOTH
        assert normalize_layer("   ") == LAYER_BOTH

    def test_unknown_rejected_never_silent_empty(self):
        normalize_layer, _WM, _LTM, _BOTH = _load_normalize_layer()
        for bad in ("working", "long_term", "both_and_more", "wm,ltm", "0", "false"):
            with pytest.raises(ValueError):
                normalize_layer(bad)


class TestBothHandlersShareOneVocabulary:
    """Source proof: both recall handlers call the shared normalizer and
    map its ValueError to HTTP 400. No handler keeps a private layer set."""

    def _read(self, rel: str) -> str:
        return (BRAIN / rel).read_text(encoding="utf-8")

    def test_endpoints_memory_uses_shared_helper(self):
        src = self._read("api/endpoints/memory.py")
        assert "normalize_layer" in src
        assert "HttpError(400" in src
        # The old private vocabulary is gone.
        assert 'layer in ("ltm", "both")' not in src
        assert "layer == \"both\"" not in src

    def test_api_memory_recall_uses_shared_helper(self):
        src = self._read("api/memory/recall.py")
        assert "normalize_layer" in src
        assert "HttpError(400" in src
        assert 'layer not in {"wm", "ltm", "all"}' not in src
        assert 'layer in {"wm", "all"}' not in src

    def test_no_second_layer_normalizer(self):
        """Exactly one normalize_layer definition in the brain package."""
        hits = []
        for path in BRAIN.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "normalize_layer":
                    hits.append(path)
        assert len(hits) == 1, f"expected one normalize_layer, found {hits}"
        assert hits[0].name == "helpers.py"
