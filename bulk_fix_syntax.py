from __future__ import annotations
import pathlib
import re
import sys
from typing import List

#!/usr/bin/env python3
"""Bulk‑fix common syntax problems left after the initial VIBE cleanup.

The script performs three independent transformations on every ``*.py`` file
in the repository (excluding virtual‑environment folders):
    pass

1. **Add a generic ``except Exception as exc`` block** after any bare ``try:``
   that lacks a handler.  The block logs the exception using the module‑level
   ``logger`` and re‑raises it.
2. **Repair broken multiline function signatures** that were split incorrectly
   during previous bulk edits (e.g. a line ending with a comma followed by a
   line that starts with ``) ->``).  The two lines are merged into a valid
   signature.
3. **Deduplicate logger imports/definitions** – keep a single ``logger =
   logging.getLogger(__name__)`` per module and remove duplicate
   ``from common.logging import logger`` imports.

After the script finishes, the total number of syntax errors should drop
dramatically, allowing ``ruff`` and ``black`` to run cleanly.
"""



ROOT = pathlib.Path(__file__).parent

# ---------------------------------------------------------------------
# 1. Insert a generic ``except`` after a bare ``try:``
# ---------------------------------------------------------------------
TRY_RE = re.compile(r"^(?P<indent>\s*)try:\s*$")
EXCEPT_OR_FINALLY_RE = re.compile(r"^\s*(except|finally)\b")


def add_generic_except(lines: List[str]) -> List[str]:
    """Ensure every ``try:`` has a body and an ``except`` block.

    * If a ``try:`` is immediately followed by an ``except``/``finally``
      without any intervening statements, we insert a ``pass`` statement
      (properly indented) so the ``try`` block is syntactically valid.
    * If the ``try`` has no handler at all, we also add a generic
      ``except Exception as exc`` block that logs and re‑raises.
    """
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = TRY_RE.match(line)
        if m:
            indent = m.group("indent")
            # Look ahead to the next non‑blank line
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            next_line = lines[j] if j < len(lines) else ""
            # Case 1: try directly followed by except/finally → insert pass
            if EXCEPT_OR_FINALLY_RE.match(next_line):
                out.append(line)
                out.append(f"{indent}    pass")
                i += 1
                continue
            # Case 2: try with no handler at all → add generic except
            if j >= len(lines) or not EXCEPT_OR_FINALLY_RE.match(next_line):
                out.append(line)
                out.append(f"{indent}    pass")
                out.append(f"{indent}except Exception as exc:")
                out.append(f"{indent}    logger.exception(\"Exception caught: %s\", exc)")
                out.append(f"{indent}    raise")
                i += 1
                continue
        out.append(line)
        i += 1
    return out

# ---------------------------------------------------------------------
# 2. Fix broken multiline function signatures
# ---------------------------------------------------------------------
def fix_broken_signature(lines: List[str]) -> List[str]:
    """Merge a line that ends with a comma and the following line that starts
    with a closing parenthesis and a return annotation.
    """
    out: List[str] = []
    skip = False
    for idx, line in enumerate(lines):
        if skip:
            skip = False
            continue
        if idx + 1 < len(lines):
            nxt = lines[idx + 1]
            if line.rstrip().endswith(",") and nxt.lstrip().startswith(")"):
                merged = line.rstrip() + " " + nxt.lstrip()
                out.append(merged)
                skip = True
                continue
        out.append(line)
    return out

# ---------------------------------------------------------------------
# 3. Remove duplicate logger imports / definitions
# ---------------------------------------------------------------------
IMPORT_LOGGER_RE = re.compile(r"^\s*from\s+common\.logging\s+import\s+logger\s*$")
LOGGER_DEF_RE = re.compile(r"^\s*logger\s*=\s*logging\.getLogger\([^\)]+\)\s*$")


def clean_logger_defs(lines: List[str]) -> List[str]:
    """Keep a single import or definition of ``logger`` per module.
    """
    out: List[str] = []
    logger_seen = False
    for line in lines:
        if IMPORT_LOGGER_RE.match(line) or LOGGER_DEF_RE.match(line):
            if not logger_seen:
                out.append(line)
                logger_seen = True
            # else: drop duplicate
            continue
        out.append(line)
    return out

# ---------------------------------------------------------------------
def process_file(path: pathlib.Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new = add_generic_except(lines)
    new = fix_broken_signature(new)
    new = clean_logger_defs(new)
    if new != lines:
        path.write_text("\n".join(new) + "\n", encoding="utf-8")
        return True
    return False


def main() -> None:
    py_files = [p for p in ROOT.rglob("*.py") if ".venv" not in p.parts]
    changed: List[str] = []
    for p in py_files:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            if process_file(p):
                changed.append(str(p.relative_to(ROOT)))
        except Exception as e:  # pragma: no cover
            print(f"Error processing {p}: {e}", file=sys.stderr)
    print(f"Bulk‑fix applied to {len(changed)} files")
    for f in changed:
        print(" •", f)


if __name__ == "__main__":
    main()
