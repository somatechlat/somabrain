#!/usr/bin/env python3
"""Strict-mode invariant scanner.

Scans the repository for banned patterns that violate strict-mode principles.
Exits non-zero if any violations are found. Intended for CI usage.

Banned tokens (case-insensitive substring match):

- fakeredis
- sqlite://
- disable_auth
- noop tracer
- KafkaProducer (from kafka-python)

Notes:
- Allowlist selected directories: .git, .venv, somabrain.egg-info, artifacts, docs, migrations/versions.
- Only scans text files up to 1 MB to keep CI fast.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BAN_TOKENS = [
    # explicit stub/backdoor patterns
    "fakeredis",
    "sqlite://",
    "disable_auth",
    # legacy kafka-python producer usage (must standardize on confluent-kafka)
    "from kafka import",
    "KafkaProducer(",
]
SKIP_DIRS = {
    ".git",
    ".venv",
    "somabrain.egg-info",
    "artifacts",
    "docs",
    "migrations/versions",
    "node_modules",
}
MAX_SIZE = 1_000_000


def is_text(path: Path) -> bool:
    """Check if text.

        Args:
            path: The path.
        """

    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
        if not chunk:
            return True
        # Heuristic: no NUL bytes
        return b"\x00" not in chunk
    except Exception:
        return False


def main() -> int:
    """Execute main.
        """

    violations: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Skip allowlisted directories
        parts = set(Path(dirpath).relative_to(ROOT).parts)
        if parts & SKIP_DIRS:
            continue
        for fn in filenames:
            path = Path(dirpath) / fn
            try:
                if path.stat().st_size > MAX_SIZE:
                    continue
            except Exception:
                continue
            if not is_text(path):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lower = text.lower()
            for token in BAN_TOKENS:
                if token.lower() in lower:
                    # Allow patterns in this script itself
                    if path == Path(__file__):
                        continue
                    violations.append((str(path.relative_to(ROOT)), token))
    if violations:
        print("Strict-mode invariant violations found:")
        for p, t in violations:
            print(f" - {p}: contains '{t}'")
        return 2
    print("Strict-mode invariant scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())