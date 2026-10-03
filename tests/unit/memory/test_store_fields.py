"""Field-fidelity guard for every memory write path.

ARCHITECTURE-INVARIANTS §5: ``embedding`` and ``tenant_id`` are first-class
top-level fields on the store body — never only nested inside ``payload``.

This suite exists because that rule already shipped broken once: the *bulk*
write paths rebuilt their body as ``{coord, payload, memory_type}`` and
silently stripped both fields, so every batch write fell back to hash vectors
and lost tenant isolation. Single writes were fine. The bug was invisible
because nothing asserted the two paths agreed.

Two kinds of check, both real:
  * behavioural — ``_seam_store_fields`` itself, which every write path now
    routes through;
  * structural — an AST walk asserting that *every* body construction in
    ``write.py`` is paired with a ``_seam_store_fields`` call in the same
    function. That is the check that fails when someone adds a seventh write
    path and forgets the helper. No mocks, no fixtures, no test doubles.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from somabrain.memory.client.write import _seam_store_fields

pytestmark = pytest.mark.no_django


class _Cfg:
    """TEST DATA — the two attributes ``_get_tenant_namespace`` reads off cfg.

    Only used as a fallback; the payloads below always carry their own tenant
    and namespace so the real settings object is never touched.
    """

    tenant = "cfg-tenant"
    namespace = "cfg-ns"


def test_tenant_id_is_promoted_from_the_payload() -> None:
    """Isolation key must land at the top level of the store body."""
    payload = {"tenant_id": "t-alpha", "namespace": "n1", "text": "x"}
    fields = _seam_store_fields(_Cfg(), {}, payload)
    assert fields["tenant_id"] == "t-alpha"


def test_tenant_alias_is_accepted() -> None:
    """``tenant`` and ``tenant_id`` are one concept, two spellings."""
    payload = {"tenant": "t-beta", "namespace": "n1"}
    assert _seam_store_fields(_Cfg(), {}, payload)["tenant_id"] == "t-beta"


def test_embedding_is_promoted_from_the_enriched_payload() -> None:
    """The vector the enrichment produced is the vector that ships."""
    enriched = {"embedding": [0.1, 0.2, 0.3]}
    payload = {"tenant_id": "t", "namespace": "n"}
    assert _seam_store_fields(_Cfg(), enriched, payload)["embedding"] == [0.1, 0.2, 0.3]


def test_embedding_falls_back_to_the_caller_payload() -> None:
    """A precomputed vector on the caller's payload must not be discarded.

    This is the path the agent takes when it already embedded the text: the
    enrichment step does not overwrite it, so only a fallback read finds it.
    """
    enriched = {"text": "x"}
    payload = {"tenant_id": "t", "namespace": "n", "embedding": [9.0, 8.0]}
    assert _seam_store_fields(_Cfg(), enriched, payload)["embedding"] == [9.0, 8.0]


def test_missing_embedding_is_omitted_not_invented() -> None:
    """No vector in, no vector out. Never fabricate a hash embedding here."""
    fields = _seam_store_fields(_Cfg(), {"text": "x"}, {"tenant_id": "t", "namespace": "n"})
    assert "embedding" not in fields


def test_enriched_embedding_wins_over_payload_embedding() -> None:
    """Enrichment is authoritative when both sides carry a vector."""
    enriched = {"embedding": [1.0]}
    payload = {"tenant_id": "t", "namespace": "n", "embedding": [2.0]}
    assert _seam_store_fields(_Cfg(), enriched, payload)["embedding"] == [1.0]


# ---------------------------------------------------------------------------
# Structural invariant — the guard that stops the paths drifting apart again.
# ---------------------------------------------------------------------------

_WRITE_MODULE = Path(__file__).resolve().parents[3] / "somabrain/memory/client/write.py"


def _body_builders(tree: ast.AST) -> dict[str, list[str]]:
    """Map each function to the names it assigns a dict literal to."""
    found: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names: list[str] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.AnnAssign | ast.Assign):
                continue
            targets = child.target if isinstance(child, ast.AnnAssign) else child.targets
            value = child.value
            if value is None or not isinstance(value, ast.Dict):
                continue
            for tgt in targets if isinstance(targets, list) else [targets]:
                if isinstance(tgt, ast.Name) and tgt.id == "body":
                    names.append(tgt.id)
        if names:
            found[node.name] = names
    return found


def _functions_calling_helper(tree: ast.AST) -> set[str]:
    """Names of functions that call ``_seam_store_fields``."""
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == "_seam_store_fields":
                    out.add(node.name)
                    break
    return out


def test_every_body_builder_routes_through_the_helper() -> None:
    """No write path may construct a store body on its own.

    Adding a write path without ``_seam_store_fields`` is how ``embedding`` and
    ``tenant_id`` get stripped again. This asserts the pairing directly on the
    module's AST so the regression cannot come back silently.
    """
    tree = ast.parse(_WRITE_MODULE.read_text())
    builders = _body_builders(tree)
    helpers = _functions_calling_helper(tree)

    orphaned = sorted(name for name in builders if name not in helpers)
    assert not orphaned, (
        "these functions build a store body but never call _seam_store_fields, "
        f"so they will strip tenant_id/embedding: {orphaned}"
    )
    # Sanity: the walk must actually have found the known write paths, or the
    # guard is vacuous.
    assert len(builders) >= 5, f"expected several body builders, found {sorted(builders)}"


def test_helper_is_the_only_place_that_mints_tenant_id() -> None:
    """``tenant_id`` must not be assembled ad hoc anywhere else in the module.

    A second construction site is a second definition of the isolation key.
    """
    tree = ast.parse(_WRITE_MODULE.read_text())
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == "_seam_store_fields":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Dict):
                continue
            for key in child.keys:
                if isinstance(key, ast.Constant) and key.value == "tenant_id":
                    offenders.append(node.name)
    assert not offenders, f"tenant_id assembled outside the helper in: {sorted(set(offenders))}"
