from __future__ import annotations
import pathlib
import re
import sys
from typing import List

#!/usr/bin/env python3
"""Add explicit ``pass`` statements to empty ``try``/``except`` blocks.

Many syntax errors in the repository are of the form:
    pass

```python
try:
    pass
except Exception as exc:
    logger.exception(...)
    raise
```

Python requires at least one statement inside the ``try`` block.  The original
code had the body removed during a previous bulk replace, leaving the ``try``
empty.  This script walks every ``*.py`` file and inserts a ``pass`` statement
when a ``try`` or ``except`` header is not followed by an indented line.
It also ensures that an ``except`` block has a body (some files only contain the
header).  After the pass is added the file is rewritten in‑place.
"""



ROOT = pathlib.Path(__file__).parent

TRY_RE = re.compile(r"^(?P<indent>\s*)try:\s*$")
EXCEPT_RE = re.compile(r"^(?P<indent>\s*)except\b.*:\s*$")


def add_passes(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # ----- try block -----
        m_try = TRY_RE.match(line)
        if m_try:
            indent = m_try.group("indent")
            # Look at next line (if any)
            next_i = i + 1
            if next_i >= len(lines) or not lines[next_i].startswith(indent + "    "):
                # No indented body – insert a pass
                out.append(line)
                out.append(f"{indent}    pass")
                i += 1
                continue
        # ----- except block -----
        m_exc = EXCEPT_RE.match(line)
        if m_exc:
            indent = m_exc.group("indent")
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
    new = add_passes(lines)
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
    print(f"Added pass statements to {len(changed)} files")
    for f in changed:
        print(" •", f)


if __name__ == "__main__":
    main()
