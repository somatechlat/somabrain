from __future__ import annotations
import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

#!/usr/bin/env python3
"""Roadmap Invariant Scanner (strict-mode).

"""



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
    pass
def __init__(self, root_path: str = ".") -> None:
        self.root_path = Path(root_path)
        self.violations: List[Tuple[str, int, str, str]] = []

def scan(self) -> List[Tuple[str, int, str, str]]:
        for file_path in self.root_path.rglob("*.py"):
            if not self._in_scope(file_path):
                continue
            if self._should_skip_file(file_path):
                continue
            if file_path.name.lower().endswith(BANNED_FILE_SUFFIXES):
                self._record_violation(file_path, 0, "BANNED_FILE", file_path.name)
                continue
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            lines = content.splitlines()
            self._check_banned_keywords(file_path, lines)
            self._check_banned_identifiers(file_path, content)
            self._check_ast_patterns(file_path, content)
        return self.violations

def _in_scope(self, file_path: Path) -> bool:
        return any(part in SCOPED_PREFIXES for part in file_path.parts)

def _should_skip_file(self, file_path: Path) -> bool:
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
        for lineno, line in enumerate(lines, 1):
            stripped = re.sub(r"#.*$", "", line)
            for keyword in BANNED_KEYWORDS:
                if keyword.lower() in stripped.lower():
                    self._record_violation(
                        file_path, lineno, "BANNED_KEYWORD", line.strip()
                    )

def _check_banned_identifiers(self, file_path: Path, content: str) -> None:
        for ident in BANNED_IDENTIFIERS:
            if re.search(rf"\\b{re.escape(ident)}\\b", content):
                self._record_violation(file_path, 0, "BANNED_IDENTIFIER", ident)

def _check_ast_patterns(self, file_path: Path, content: str) -> None:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            tree = ast.parse(content)
        except SyntaxError:
            return

class ShimVisitor(ast.NodeVisitor):
    pass
def __init__(self) -> None:
                self.found = False

def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
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
        self.violations.append((str(file_path), lineno, typ, detail))

def report(self) -> str:
        if not self.violations:
            return "✅ Roadmap invariants satisfied"
        lines = ["❌ Roadmap violations detected:"]
        for path, lineno, typ, detail in self.violations:
            lines.append(f"- {path}:{lineno} [{typ}] {detail}")
        return "\n".join(lines)


def main() -> None:
    scanner = RoadmapInvariantScanner()
    scanner.scan()
    print(scanner.report())
    sys.exit(1 if scanner.violations else 0)


if __name__ == "__main__":
    main()
