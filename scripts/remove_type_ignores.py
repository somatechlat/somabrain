"""Module remove_type_ignores."""

import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def process_file(path: str) -> None:
    """Execute process file.

        Args:
            path: The path.
        """

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    changed = False
    for line in lines:
        # Remove any trailing '# type: ignore' (with optional brackets)
        new_line = re.sub(r"\s+#\s*type:\s*ignore(?:\[[^\]]*\])?", "", line)
        if new_line != line:
            changed = True
        new_lines.append(new_line)
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"cleaned {path}")


for dirpath, _, filenames in os.walk(ROOT):
    for fn in filenames:
        if fn.endswith(".py"):
            process_file(os.path.join(dirpath, fn))