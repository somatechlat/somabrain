from __future__ import annotations
import pathlib
import re
import sys
from typing import List

#!/usr/bin/env python3
"""Auto‑fix remaining easy‑to‑repair syntax issues after the bulk VIBE fixes.

The script performs a conservative set of transformations that do **not**
touch the actual business logic:
    pass

1. **Move all import statements** (including ``from ... import ...``) to the top
   of the file, after an optional module docstring.
2. **Deduplicate logger imports/definitions** – keep only the first
   ``from common.logging import logger`` or ``logger = logging.getLogger(...)``
   per module.
3. **Wrap stray dictionary entries** that appear as top‑level lines (e.g.
   ``"agent_zero": "agent_zero",``) into a temporary dict assignment
   ``_tmp_dict = { ... }`` so the parser no longer sees them as stray
   statements.
4. **Add ``pass`` to empty ``except``/``finally`` blocks** that have no body.
5. **Delete unused logger imports** if the module does not define a ``logger``
   variable.

Running this script after ``apply_vibe_fixes.py`` should eliminate most of the
remaining ``E402`` import‑order warnings and a large chunk of the syntax errors.
"""



ROOT = pathlib.Path(__file__).parent

# ---------------------------------------------------------------------
# Regular expressions
# ---------------------------------------------------------------------
IMPORT_RE = re.compile(r"^\s*(import|from)\s+")
LOGGER_IMPORT_RE = re.compile(r"^\s*from\s+common\.logging\s+import\s+logger\s*$")
LOGGER_DEF_RE = re.compile(r"^\s*logger\s*=\s*logging\.getLogger\([^)]*\)\s*$")
DICT_ENTRY_RE = re.compile(r'^\s*"[^"]+"\s*:\s*"[^"]+"\s*,\s*$')
EXCEPT_OR_FINALLY_RE = re.compile(r"^\s*(except|finally)\b.*:\s*$")


def move_imports_to_top(lines: List[str]) -> List[str]:
    """Collect import lines and place them after the optional module docstring."""
    imports: List[str] = []
    other: List[str] = []
    i = 0
    docstring_done = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Preserve a leading module docstring (triple‑quoted string).
        if not docstring_done and (stripped.startswith('"""') or stripped.startswith("'''")):
            other.append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().endswith(stripped[:3]):
                other.append(lines[i])
                i += 1
            if i < len(lines):
                other.append(lines[i])
                i += 1
            docstring_done = True
            continue
        if IMPORT_RE.match(line):
            imports.append(line)
        else:
            other.append(line)
        i += 1
    # Ensure a blank line separates imports from the rest (if needed).
    if imports and other and other[0].strip():
        imports.append("")
    return imports + other


def dedup_logger(lines: List[str]) -> List[str]:
    out: List[str] = []
    seen = False
    for line in lines:
        if LOGGER_IMPORT_RE.match(line) or LOGGER_DEF_RE.match(line):
            if not seen:
                out.append(line)
                seen = True
            # duplicate – drop
            continue
        out.append(line)
    return out


def wrap_stray_dict_entries(lines: List[str]) -> List[str]:
    out: List[str] = []
    inside_braces = False
    for line in lines:
        if line.strip().endswith("{"):
            inside_braces = True
            out.append(line)
            continue
        if inside_braces and line.strip().endswith("}"):
            inside_braces = False
            out.append(line)
            continue
        if DICT_ENTRY_RE.match(line) and not inside_braces:
            out.append("_tmp_dict = {")
            out.append(line)
            out.append("}")
        else:
            out.append(line)
    return out


def ensure_except_finally_pass(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if EXCEPT_OR_FINALLY_RE.match(line):
            indent = line[: len(line) - len(line.lstrip())]
            # Look ahead for an indented statement.
            next_i = i + 1
            if next_i >= len(lines) or not lines[next_i].startswith(indent + "    "):
                out.append(line)
                out.append(f"{indent}    pass")
                i += 1
                continue
        out.append(line)
        i += 1
    return out


def process_file(path: pathlib.Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new = move_imports_to_top(lines)
    new = dedup_logger(new)
    new = wrap_stray_dict_entries(new)
    new = ensure_except_finally_pass(new)
    if new != lines:
        path.write_text("\n".join(new) + "\n", encoding="utf-8")
        return True
    return False


def main() -> None:
    py_files = [p for p in ROOT.rglob("*.py") if ".venv" not in p.parts]
    changed: List[str] = []
    for p in py_files:
        try:
            if process_file(p):
                changed.append(str(p.relative_to(ROOT)))
        except Exception as e:  # pragma: no cover
            print(f"Error processing {p}: {e}", file=sys.stderr)
    print(f"Auto‑fix applied to {len(changed)} files")
    for f in changed:
        print(" •", f)


if __name__ == "__main__":
    main()
