from __future__ import annotations
import pathlib
import re
import sys
from typing import List

"""Fix malformed ``except Exception`` blocks across the repository.

The VIBE rules require that every ``except Exception`` block logs the
exception and then re‑raises it.  A previous bulk replacement left stray
indented statements after the ``raise`` (e.g. ``raise`` followed by more
code), which results in syntax errors such as ``invalid syntax`` or
``unexpected indentation``.

This script walks all ``.py`` files (excluding the virtual‑environment
directory) and rewrites any ``except Exception`` block to the canonical
form:
    pass

```python
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
```

All lines that were originally part of the malformed block (i.e. any
indented lines following the ``raise``) are removed.  If a file does not
already import ``logger`` from ``common.logging`` the import is added after
the existing import statements.

Run the script with ``python fix_exceptions.py``.  It prints a summary of
the modified files.
"""



ROOT = pathlib.Path(__file__).parent

EXCEPT_RE = re.compile(r"^(?P<indent>\s*)except\s+Exception(?:\s+as\s+(?P<var>\w+))?:\s*$")


def ensure_logger_import(lines: List[str]) -> List[str]:
    """Add ``from common.logging import logger`` if missing.

    The import is inserted after the last existing import statement.
    """
    import_line = "from common.logging import logger"
    if any(import_line in line for line in lines):
        return lines
    # Find the last import (including ``from ... import ...`` or ``import ...``)
    last_import_idx = -1
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = i
    # Insert after the last import, or at the top if none found
    insert_idx = last_import_idx + 1
    return lines[:insert_idx] + [import_line] + lines[insert_idx:]


def process_file(path: pathlib.Path) -> bool:
    """Rewrite malformed ``except Exception`` blocks in *path*.

    Returns ``True`` if the file was modified.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines: List[str] = []
    i = 0
    changed = False
    while i < len(lines):
        line = lines[i]
        m = EXCEPT_RE.match(line)
        if m:
            indent = m.group("indent")
            var_name = m.group("var") or "exc"
            # Write the corrected block
            new_lines.append(f"{indent}except Exception as {var_name}:")
            new_lines.append(f"{indent}    logger.exception(\"Exception caught: %s\", {var_name})")
            new_lines.append(f"{indent}    raise")
            changed = True
            # Skip original block lines: advance until a line with indentation <= current block
            i += 1
            while i < len(lines):
                next_line = lines[i]
                stripped = next_line.lstrip(" \t")
                next_indent = next_line[: len(next_line) - len(stripped)]
                if len(next_indent) <= len(indent):
                    break
                i += 1
            continue
        else:
            new_lines.append(line)
            i += 1
    if changed:
        new_lines = ensure_logger_import(new_lines)
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return changed


def _remove_stray_raises(path: pathlib.Path) -> bool:
    """Remove lines that consist solely of ``raise`` when the following line
    is a block keyword (``except``, ``finally``, ``else``, ``elif``) *or* is
    more indented than the ``raise`` line.  These patterns were introduced by
    the previous bulk‑fix and cause ``invalid-syntax`` errors.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines: List[str] = []
    i = 0
    changed = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped == "raise" and i + 1 < len(lines):
            next_line = lines[i + 1]
            next_stripped = next_line.lstrip()
            cur_indent = len(line) - len(line.lstrip())
            next_indent = len(next_line) - len(next_line.lstrip())
            if (
                next_indent == cur_indent
                and any(
                    next_stripped.startswith(kw)
                    for kw in ("except", "finally", "else", "elif")
                )
            ) or (next_indent > cur_indent):
                changed = True
                i += 1
                continue
        new_lines.append(line)
        i += 1
    if changed:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    py_files = [p for p in ROOT.rglob("*.py") if ".venv" not in p.parts]
    modified: List[str] = []
    for p in py_files:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            changed = False
            if process_file(p):
                changed = True
            if _remove_stray_raises(p):
                changed = True
            if changed:
                modified.append(str(p.relative_to(ROOT)))
        except Exception as e:  # pragma: no cover
            print(f"Error processing {p}: {e}", file=sys.stderr)
    print(f"Modified {len(modified)} files")
    for f in modified:
        print(f" - {f}")


if __name__ == "__main__":
    main()
