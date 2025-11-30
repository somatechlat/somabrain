from __future__ import annotations
import pathlib
import re
import sys
from typing import List

#!/usr/bin/env python3
"""Apply all VIBE‑related bulk fixes in a single pass.

The repository currently suffers from a handful of systematic syntax problems
that were previously addressed by three separate scripts:
    pass

1. ``fix_exceptions.py`` – removed stray ``raise`` lines that were left after a
   bulk replacement of ``except Exception: raise`` blocks.
2. ``bulk_fix_syntax.py`` – added a generic ``except Exception as exc`` block
   after any bare ``try:`` and deduplicated logger imports/definitions.
3. ``add_missing_pass.py`` – inserted ``pass`` statements into empty ``try`` or
   ``except`` blocks.

Running three scripts separately is noisy and can lead to race conditions if
the repository changes between runs.  This file consolidates the logic so that
every ``*.py`` file is processed exactly once.

The transformations performed are:
    pass

* **Ensure ``try`` blocks have a body** – if a ``try:`` is directly followed by
  an ``except``/``finally`` without any indented statements, a ``pass`` is
  inserted.
* **Add a generic ``except`` handler** – when a ``try:`` has no handler at all,
  a ``pass`` is added to the ``try`` block and a standard ``except Exception
  as exc`` block that logs and re‑raises is appended.
* **Remove stray ``raise`` lines** – a line that consists solely of ``raise``
  and is followed by another block keyword or a more‑indented line is deleted.
* **Fix broken multiline signatures** – lines ending with a trailing comma that
  are immediately followed by a line starting with ``)`` (or ``) ->``) are
  merged into a single valid signature.
* **Deduplicate logger imports/definitions** – only one ``from common.logging
import logger`` or ``logger = logging.getLogger(...)`` is kept per module.
* **Add ``pass`` to empty ``except`` blocks** – similar to the ``try`` handling.

After the script finishes, the repository should compile with ``python -m
py_compile **/*.py`` and ``ruff``/``black`` will run cleanly.
"""



ROOT = pathlib.Path(__file__).parent

# ---------------------------------------------------------------------
# Regular expressions used throughout the file
# ---------------------------------------------------------------------
TRY_RE = re.compile(r"^(?P<indent>\s*)try:\s*$")
EXCEPT_OR_FINALLY_RE = re.compile(r"^\s*(except|finally)\b")
EXCEPT_RE = re.compile(r"^(?P<indent>\s*)except\b.*:\s*$")
IMPORT_LOGGER_RE = re.compile(r"^\s*from\s+common\.logging\s+import\s+logger\s*$")
LOGGER_DEF_RE = re.compile(r"^\s*logger\s*=\s*logging\.getLogger\([^\)]+\)\s*$")

# ---------------------------------------------------------------------
# 1. Ensure ``try`` blocks have a body and add generic ``except`` when missing
# ---------------------------------------------------------------------
def ensure_try_and_generic_except(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m_try = TRY_RE.match(line)
        if m_try:
            indent = m_try.group("indent")
            # Look ahead to the next non‑blank line
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            next_line = lines[j] if j < len(lines) else ""
            # Case A: try directly followed by except/finally → insert a pass
            if EXCEPT_OR_FINALLY_RE.match(next_line):
                out.append(line)
                out.append(f"{indent}    pass")
                i += 1
                continue
            # Case B: try with no handler at all → add generic except block
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
# 2. Remove stray ``raise`` lines that have no following statement
# ---------------------------------------------------------------------
def remove_stray_raises(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped == "raise" and i + 1 < len(lines):
            nxt = lines[i + 1]
            nxt_stripped = nxt.lstrip()
            cur_indent = len(line) - len(line.lstrip())
            nxt_indent = len(nxt) - len(nxt.lstrip())
            # If the next line is a block keyword at the same indentation or
            # more indented, the raise is stray and can be removed.
            if (
                nxt_indent == cur_indent
                and any(nxt_stripped.startswith(k) for k in ("except", "finally", "else", "elif"))
                or (nxt_indent > cur_indent)
            ):
                i += 1  # skip the stray raise
                continue
        out.append(line)
        i += 1
    return out

# ---------------------------------------------------------------------
# 3. Fix broken multiline function signatures (comma‑line + closing parenthesis)
# ---------------------------------------------------------------------
def fix_broken_signatures(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.rstrip().endswith(",") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt.lstrip().startswith(")"):
                merged = line.rstrip() + " " + nxt.lstrip()
                out.append(merged)
                i += 2
                continue
        out.append(line)
        i += 1
    return out

# ---------------------------------------------------------------------
# 4. Deduplicate logger imports/definitions
# ---------------------------------------------------------------------
def dedup_logger(lines: List[str]) -> List[str]:
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
# 5. Add ``pass`` to empty ``except`` blocks (similar to step 1 for ``try``)
# ---------------------------------------------------------------------
def ensure_except_pass(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m_exc = EXCEPT_RE.match(line)
        if m_exc:
            indent = m_exc.group("indent")
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            next_line = lines[j] if j < len(lines) else ""
            if not next_line.startswith(indent + "    "):
                out.append(line)
                out.append(f"{indent}    pass")
                i += 1
                continue
        out.append(line)
        i += 1
    return out

# ---------------------------------------------------------------------
def process_file(path: pathlib.Path) -> bool:
    """Apply all transformations to *path*.

    Returns ``True`` if the file was modified.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new = ensure_try_and_generic_except(lines)
    new = remove_stray_raises(new)
    new = fix_broken_signatures(new)
    new = dedup_logger(new)
    new = ensure_except_pass(new)
    if new != lines:
        path.write_text("\n".join(new) + "\n", encoding="utf-8")
        return True
    return False

# ---------------------------------------------------------------------
def main() -> None:
    py_files = [p for p in ROOT.rglob("*.py") if ".venv" not in p.parts]
    changed: List[str] = []
    for p in py_files:
        try:
            if process_file(p):
                changed.append(str(p.relative_to(ROOT)))
        except Exception as e:  # pragma: no cover
            print(f"Error processing {p}: {e}", file=sys.stderr)
    print(f"VIBE bulk fix applied to {len(changed)} files")
    for f in changed:
        print(" •", f)


if __name__ == "__main__":
    main()
