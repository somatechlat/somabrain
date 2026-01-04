#!/usr/bin/env python3
"""Roadmap Invariant Scanner (strict-mode).

Fails the build when banned shims/fallbacks or legacy keywords show up.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

BANNED_KEYWORDS = [
    "fakeredis",
    "sqlite://",
    "noop tracer",
    "disable_auth",
    "KafkaProducer",
]

BANNED_FILE_SUFFIXES = ("_shim.py", "_fallback.py")
BANNED_IDENTIFIERS = ["_record_outbox", "MemoryRecallClient"]
SCOPED_PREFIXES = ("somabrain", "config", "clients")


class RoadmapInvariantScanner:
    """Roadmapinvariantscanner class implementation."""

    def __init__(self, root_path: str = ".") -> None:
        """Initialize the instance."""

        self.root_path = Path(root_path)
        self.violations: List[Tuple[str, int, str, str]] = []

    def scan(self) -> List[Tuple[str, int, str, str]]:
        """Execute scan."""

        for file_path in self.root_path.rglob("*.py"):
            if not self._in_scope(file_path):
                continue
            if self._should_skip_file(file_path):
                continue
            if file_path.name.lower().endswith(BANNED_FILE_SUFFIXES):
                self._record_violation(file_path, 0, "BANNED_FILE", file_path.name)
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            lines = content.splitlines()
            self._check_banned_keywords(file_path, lines)
            self._check_banned_identifiers(file_path, content)
            self._check_ast_patterns(file_path, content)
        return self.violations

    def _in_scope(self, file_path: Path) -> bool:
        """Execute in scope.

        Args:
            file_path: The file_path.
        """

        return any(part in SCOPED_PREFIXES for part in file_path.parts)

    def _should_skip_file(self, file_path: Path) -> bool:
        """Execute should skip file.

        Args:
            file_path: The file_path.
        """

        skip_parts = {
            "tests",
            "node_modules",
            "dist",
            "build",
            "__pycache__",
            ".venv",
            "venv",
        }
        return any(part in skip_parts for part in file_path.parts)

    def _check_banned_keywords(self, file_path: Path, lines: List[str]) -> None:
        """Execute check banned keywords.

        Args:
            file_path: The file_path.
            lines: The lines.
        """

        for lineno, line in enumerate(lines, 1):
            stripped = re.sub(r"#.*$", "", line)
            for keyword in BANNED_KEYWORDS:
                if keyword.lower() in stripped.lower():
                    self._record_violation(
                        file_path, lineno, "BANNED_KEYWORD", line.strip()
                    )

    def _check_banned_identifiers(self, file_path: Path, content: str) -> None:
        """Execute check banned identifiers.

        Args:
            file_path: The file_path.
            content: The content.
        """

        for ident in BANNED_IDENTIFIERS:
            if re.search(rf"\\b{re.escape(ident)}\\b", content):
                self._record_violation(file_path, 0, "BANNED_IDENTIFIER", ident)

    def _check_ast_patterns(self, file_path: Path, content: str) -> None:
        """Execute check ast patterns.

        Args:
            file_path: The file_path.
            content: The content.
        """

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        class ShimVisitor(ast.NodeVisitor):
            """Shimvisitor class implementation."""

            def __init__(self) -> None:
                """Initialize the instance."""

                self.found = False

            def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
                """Execute visit Name.

                Args:
                    node: The node.
                """

                if node.id in BANNED_IDENTIFIERS:
                    self.found = True
                self.generic_visit(node)

        visitor = ShimVisitor()
        visitor.visit(tree)
        if visitor.found:
            self._record_violation(file_path, 0, "BANNED_IDENTIFIER", "AST usage")

    def _record_violation(
        self, file_path: Path, lineno: int, typ: str, detail: str
    ) -> None:
        """Execute record violation.

        Args:
            file_path: The file_path.
            lineno: The lineno.
            typ: The typ.
            detail: The detail.
        """

        self.violations.append((str(file_path), lineno, typ, detail))

    def report(self) -> str:
        """Execute report."""

        if not self.violations:
            return "✅ Roadmap invariants satisfied"
        lines = ["❌ Roadmap violations detected:"]
        for path, lineno, typ, detail in self.violations:
            lines.append(f"- {path}:{lineno} [{typ}] {detail}")
        return "\n".join(lines)


def main() -> None:
    """Execute main."""

    scanner = RoadmapInvariantScanner()
    scanner.scan()
    print(scanner.report())
    sys.exit(1 if scanner.violations else 0)


if __name__ == "__main__":
    main()
