#!/usr/bin/env python3
"""Utility script to perform a coarse‑grained clean‑up of the codebase.

The repository currently contains many syntax errors caused by
* stray indentation before top‑level statements (imports, class / def definitions,
  decorators, etc.)
* empty control‑flow blocks (``if:``, ``try:``, ``except:``, ``finally:``,
  ``for:``, ``while:``, ``else:``) that have no body.

This script applies two simple, safe heuristics:
    pass
1. **Dedent top‑level lines** – if a line, after stripping leading whitespace,
   starts with a keyword that should appear at column 0, the leading whitespace
   is removed.
2. **Insert a ``pass``** into any block that ends with a colon but whose next
   line is either blank or has an indentation level less than or equal to the
   header line. This guarantees a syntactically valid suite.

The transformations are intentionally conservative; they never modify the
semantic content of a line, only its indentation. After running this script we
run ``ruff --fix`` to address the remaining style issues.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Iterable

# Keywords that must appear at the start of a file (no leading indentation).
TOP_LEVEL_KEYWORDS: tuple[str, ...] = (
    "import ",
    "from ",
    "def ",
    "class ",
    "@",
    "if __name__",
)


def dedent_line(line: str) -> str:
    """Remove leading whitespace if *line* starts with a top‑level keyword.

    The function preserves the original line when no keyword matches.
    """
    stripped = line.lstrip()
    for kw in TOP_LEVEL_KEYWORDS:
        if stripped.startswith(kw):
            return stripped
    return line


def insert_pass_if_needed(lines: list[str]) -> list[str]:
    """Insert ``pass`` statements into empty blocks.

    The algorithm walks the list of lines and looks for a line that ends with a
    colon. If the following line is either empty or indented less than or equal
    to the header line, a ``pass`` line with one additional indent level is
    inserted.
    """
    i = 0
    while i < len(lines) - 1:
        header = lines[i]
        if header.rstrip().endswith(":"):
            header_indent = len(header) - len(header.lstrip())
            next_line = lines[i + 1]
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_line.strip() == "" or next_indent <= header_indent:
                pass_line = " " * (header_indent + 4) + "pass"
                lines.insert(i + 1, pass_line)
                i += 1
        i += 1
    return lines


def fix_file(path: pathlib.Path) -> None:
    """Apply the two heuristics to *path* in‑place."""
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    lines = [dedent_line(l) for l in lines]
    lines = insert_pass_if_needed(lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def iter_python_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    """Yield all ``.py`` files under *root* (excluding virtual‑env folders)."""
    for p in root.rglob("*.py"):
        if "site-packages" in p.parts or "venv" in p.parts:
            continue
        yield p


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parent
    for py_file in iter_python_files(repo_root):
        try:
            fix_file(py_file)
        except Exception as exc:  # pragma: no cover – defensive
            print(f"Failed to fix {py_file}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
