"""V1 CRITICAL: every write path must forward SFM seam fields top-level.

Regression guard: two body builders stripped ``embedding`` and ``tenant_id``
so every stored memory fell back to hash vectors and lost tenant isolation.
The correct seam is ``build_store_payload`` (transport.py) +
``_seam_store_fields`` (write.py) / ``seam_store_fields`` (payload.py).

This suite asserts:
  1. ``build_store_body`` forwards importance / belief_confidence /
     belief_polarity top-level when present.
  2. ``seam_store_fields`` promotes embedding / tenant_id from payload.
  3. The outbox paths in ``remember.py`` route through ``build_store_body``
     (AST structural check — no duplicate ``{coord, payload, memory_type}``
     dict literals).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from somabrain.memory.payload import build_store_body, seam_store_fields

pytestmark = pytest.mark.no_django

REPO_ROOT = Path(__file__).resolve().parents[2]


class _Cfg:
    """TEST DATA — the two attributes ``_get_tenant_namespace`` reads off cfg."""

    tenant = "cfg-tenant"
    namespace = "cfg-ns"


# ---------------------------------------------------------------------------
# 1. build_store_body forwards SFM scalars top-level
# ---------------------------------------------------------------------------


def test_build_store_body_forwards_importance() -> None:
    body = build_store_body(
        coord="1.0,2.0,3.0",
        payload={"text": "x"},
        memory_type="episodic",
        importance=0.85,
    )
    assert body["importance"] == 0.85


def test_build_store_body_forwards_belief_confidence() -> None:
    body = build_store_body(
        coord="1.0,2.0,3.0",
        payload={"text": "x"},
        memory_type="belief",
        belief_confidence=0.7,
        belief_polarity="positive",
    )
    assert body["belief_confidence"] == 0.7
    assert body["belief_polarity"] == "positive"


def test_build_store_body_omits_absent_scalars() -> None:
    body = build_store_body(
        coord="1.0,2.0,3.0",
        payload={"text": "x"},
        memory_type="episodic",
    )
    assert "importance" not in body
    assert "belief_confidence" not in body
    assert "belief_polarity" not in body


def test_build_store_body_forwards_embedding_and_tenant() -> None:
    body = build_store_body(
        coord="1.0,2.0,3.0",
        payload={"text": "x"},
        memory_type="episodic",
        embedding=[0.1, 0.2, 0.3],
        tenant_id="t-42",
    )
    assert body["embedding"] == [0.1, 0.2, 0.3]
    assert body["tenant_id"] == "t-42"


def test_build_store_body_seam_fields_merged() -> None:
    """Explicit keyword args win over a stale seam_fields dict."""
    body = build_store_body(
        coord="1.0,2.0,3.0",
        payload={"text": "x"},
        memory_type="episodic",
        seam_fields={"tenant_id": "stale", "importance": 0.1},
        tenant_id="fresh",
        importance=0.9,
    )
    assert body["tenant_id"] == "fresh"
    assert body["importance"] == 0.9


# ---------------------------------------------------------------------------
# 2. seam_store_fields promotes embedding / tenant_id
# ---------------------------------------------------------------------------


def test_seam_store_fields_promotes_embedding_from_enriched() -> None:
    fields = seam_store_fields(
        _Cfg(), {"embedding": [1.0, 2.0]}, {"tenant_id": "t", "namespace": "n"}
    )
    assert fields["embedding"] == [1.0, 2.0]


def test_seam_store_fields_promotes_tenant_id() -> None:
    fields = seam_store_fields(_Cfg(), {}, {"tenant_id": "t-x", "namespace": "n"})
    assert fields["tenant_id"] == "t-x"


def test_seam_store_fields_lifts_importance_from_signals() -> None:
    fields = seam_store_fields(
        _Cfg(), {}, {"tenant_id": "t", "namespace": "n", "signals": {"importance": 0.5}}
    )
    assert fields["importance"] == 0.5


# ---------------------------------------------------------------------------
# 3. Structural: no duplicate store-body dict literals outside payload.py
# ---------------------------------------------------------------------------

REMEMBER_MODULE = REPO_ROOT / "somabrain/memory/remember.py"
WRITE_MODULE = REPO_ROOT / "somabrain/memory/client/write.py"


def _body_dict_literals(tree: ast.AST) -> dict[str, list[str]]:
    """Map each function to names assigned a dict literal with 'coord' key."""
    found: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names: list[str] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.AnnAssign | ast.Assign):
                continue
            value = child.value
            if value is None or not isinstance(value, ast.Dict):
                continue
            # Check if this dict has a 'coord' key
            has_coord = any(
                isinstance(k, ast.Constant) and k.value == "coord" for k in value.keys
            )
            if not has_coord:
                continue
            targets = (
                child.target if isinstance(child, ast.AnnAssign) else child.targets
            )
            for tgt in targets if isinstance(targets, list) else [targets]:
                if isinstance(tgt, ast.Name):
                    names.append(tgt.id)
        if names:
            found[node.name] = names
    return found


def _functions_using_build_store_body(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in ("build_store_body", "build_store_payload"):
                    out.add(node.name)
                    break
    return out


def test_remember_py_routes_through_build_store_body() -> None:
    """remember.py outbox paths must call build_store_body, not build dicts."""
    tree = ast.parse(REMEMBER_MODULE.read_text())
    builders = _body_dict_literals(tree)
    helpers = _functions_using_build_store_body(tree)

    orphaned = sorted(name for name in builders if name not in helpers)
    assert not orphaned, (
        "remember.py functions build a {coord,...} dict but never call "
        f"build_store_body — they will strip seam fields: {orphaned}"
    )


def test_write_py_routes_through_seam_helper() -> None:
    """write.py body builders must pair with _seam_store_fields or build_store_body."""
    tree = ast.parse(WRITE_MODULE.read_text())
    builders = _body_dict_literals(tree)

    seam_callers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in (
                    "_seam_store_fields",
                    "build_store_body",
                    "build_store_payload",
                ):
                    seam_callers.add(node.name)
                    break

    orphaned = sorted(name for name in builders if name not in seam_callers)
    assert not orphaned, (
        "write.py functions build a {coord,...} dict but never call "
        f"_seam_store_fields/build_store_body: {orphaned}"
    )
