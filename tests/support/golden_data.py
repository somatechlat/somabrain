"""Utilities for loading golden datasets used in regression tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "golden"


def iter_jsonl(name: str) -> Iterator[dict[str, Any]]:
    """Yield dictionaries from a JSON-lines file stored in the golden dataset."""
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
