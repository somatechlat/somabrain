"""Invariant: adaptive/learning modules must not contain inline magic numbers.

This test enforces that all tunables live in common.config.settings (or derived
constants), preventing regressions where literals get reintroduced.
"""

from __future__ import annotations

import ast
from pathlib import Path


# Modules to scan for forbidden inline numeric literals at module/class scope
TARGET_FILES = [
    Path("somabrain/context/builder.py"),
    Path("somabrain/learning/adaptation.py"),
    Path("somabrain/neuromodulators.py"),
    Path("somabrain/adaptive_neuromodulators.py"),
]


class _ScopeVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.offenders: list[str] = []
        self._function_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._function_depth == 0:
            self._check_constant(node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._function_depth == 0 and node.value is not None:
            self._check_constant(node.value, node.lineno)
        self.generic_visit(node)

    def _check_constant(self, value: ast.AST, lineno: int) -> None:
        if isinstance(value, ast.Constant) and isinstance(value.value, (int, float)):
            self.offenders.append(f"{self.path}:{lineno}: numeric literal at module/class scope")


def test_no_magic_numbers_in_adaptive_modules():
    offenders: list[str] = []
    for path in TARGET_FILES:
        tree = ast.parse(path.read_text())
        v = _ScopeVisitor(path)
        v.visit(tree)
        offenders.extend(v.offenders)
    assert not offenders, "Magic numeric literals found (module/class scope):\n" + "\n".join(offenders)
