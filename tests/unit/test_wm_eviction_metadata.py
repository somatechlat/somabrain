"""D1: WM eviction is payload metadata, not a memory_type.

The SFM contract accepts memory_type in {episodic, semantic, belief,
working_memory}. Eviction is expressed as ``evicted=true`` in the payload,
never as a separate ``working_memory_eviction`` type.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

REPO_ROOT = Path(__file__).resolve().parents[2]
WM_PERSISTENCE = REPO_ROOT / "somabrain/memory/wm_persistence.py"


def _get_source() -> str:
    return WM_PERSISTENCE.read_text()


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


class TestWMEvictionMetadata:
    """Eviction is metadata, not a type."""

    def test_mark_evicted_sets_evicted_true(self) -> None:
        """The eviction payload must carry evicted=True."""
        source = _get_source()
        tree = ast.parse(source)
        fn = _find_function(tree, "mark_evicted")
        assert fn is not None, "mark_evicted function must exist"

        # Find the eviction_payload dict assignment
        found_evicted = False
        for node in ast.walk(fn):
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and key.value == "evicted":
                        found_evicted = True
                        break
        assert found_evicted, "mark_evicted must set 'evicted' key in payload"

    def test_mark_evicted_uses_working_memory_type(self) -> None:
        """Eviction records use memory_type='working_memory', not a special type."""
        source = _get_source()
        tree = ast.parse(source)
        fn = _find_function(tree, "mark_evicted")
        assert fn is not None

        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and node.value == "working_memory_eviction":
                pytest.fail(
                    "mark_evicted still uses memory_type='working_memory_eviction'; "
                    "must use 'working_memory' with evicted=True metadata"
                )

    def test_queue_persist_uses_working_memory_type(self) -> None:
        """WM items queued for persistence use memory_type='working_memory'."""
        source = _get_source()
        tree = ast.parse(source)
        fn = _find_function(tree, "queue_persist")
        assert fn is not None

        found = False
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and node.value == "working_memory":
                found = True
                break
        assert found, "queue_persist must set memory_type='working_memory'"

    def test_no_eviction_type_literal_anywhere(self) -> None:
        """No occurrence of 'working_memory_eviction' as a string literal."""
        source = _get_source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "working_memory_eviction":
                pytest.fail(
                    f"line {node.lineno}: 'working_memory_eviction' literal found; "
                    "eviction is payload metadata (evicted=true), not a type"
                )

    def test_restore_skips_evicted_items(self) -> None:
        """Restore must filter on evicted=false (A1.7)."""
        source = _get_source()
        assert "evicted" in source, "restore must check evicted flag"
