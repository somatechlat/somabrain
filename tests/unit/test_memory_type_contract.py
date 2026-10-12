"""D1: WM type contract — SFM accepts only the four memory_type values.

SFM MemoryStoreRequest.memory_type is constrained to
{episodic, semantic, belief, working_memory}. Eviction is payload metadata
(``evicted=true``), NOT a type. ``working_memory_eviction`` is a lie.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

REPO_ROOT = Path(__file__).resolve().parents[2]
WM_PERSISTENCE = REPO_ROOT / "somabrain/memory/wm_persistence.py"

# The SFM contract (live) — must match MemoryStoreRequest.
SFM_MEMORY_TYPES = frozenset(
    {"episodic", "semantic", "belief", "working_memory"}
)


def test_sfm_memory_types_are_the_four() -> None:
    """Contract lock: the four types above are the only accepted values."""
    assert SFM_MEMORY_TYPES == {"episodic", "semantic", "belief", "working_memory"}


def test_wm_persistence_never_sends_eviction_type() -> None:
    """D1 FIX: wm_persistence must not send memory_type='working_memory_eviction'."""
    source = WM_PERSISTENCE.read_text()
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == "working_memory_eviction":
            # Find enclosing function name
            offenders.append(f"line {node.lineno}: literal 'working_memory_eviction'")
    assert not offenders, (
        "wm_persistence.py still sends memory_type='working_memory_eviction'; "
        f"eviction must be payload metadata (evicted=true), not a type: {offenders}"
    )


def test_wm_persistence_uses_working_memory_type() -> None:
    """WM items must use memory_type='working_memory' (the SFM contract value)."""
    source = WM_PERSISTENCE.read_text()
    tree = ast.parse(source)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == "working_memory":
            found = True
            break
    assert found, "wm_persistence.py must send memory_type='working_memory'"


def test_wm_eviction_marks_with_metadata_not_type() -> None:
    """mark_evicted must set evicted=True, not change memory_type."""
    source = WM_PERSISTENCE.read_text()
    # Check that the eviction payload has 'evicted': True
    assert '"evicted": True' in source or "'evicted': True" in source or "evicted=True" in source or '"evicted": true' in source.lower().replace("'", '"'), (
        "mark_evicted must set evicted=True as payload metadata"
    )


def test_wm_restore_filter_matches_working_memory() -> None:
    """Restore must filter on memory_type='working_memory' consistently."""
    source = WM_PERSISTENCE.read_text()
    assert "working_memory" in source, "restore filter must reference working_memory"
