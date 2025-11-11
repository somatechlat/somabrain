import os
import re
from pathlib import Path


BAN_PATTERNS = [
    # No banned terms - strict mode enforced
    r"fakeredis",
    r"sqlite://",
    r"disable_?auth",
    r"SOMABRAIN_DISABLE_",
]

ALLOW_PATH_SUBSTRINGS = [
    "/tests/fixtures/",
    "/docs/",  # Documentation legitimately discusses banned patterns
    "ROADMAP_CANONICAL.md",  # Roadmap explains what's banned
    "ROADMAP_IMPLEMENTATION.md",  # Implementation notes reference banned patterns
    "/scripts/strict_invariants.py",  # This script defines what's banned
    "/tests/invariants/",  # Test files define banned patterns they're checking for
]

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "artifacts", "benchmarks"}
EXTENSIONS = {".py", ".yaml", ".yml", ".toml", ".ini", ".md"}


def _should_scan(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    return path.suffix in EXTENSIONS


def test_no_banned_tokens():
    root = Path(__file__).resolve().parents[2]
    banned_hits = []
    patterns = [(pat, re.compile(pat, re.IGNORECASE)) for pat in BAN_PATTERNS]
    for p in root.rglob("*"):
        # Skip this test file itself to avoid false positives on its own patterns
        if p == Path(__file__):
            continue
        if not p.is_file() or not _should_scan(p):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lower_path = str(p)
        if any(sub in lower_path for sub in ALLOW_PATH_SUBSTRINGS):
            continue
        for raw, rx in patterns:
            for m in rx.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                snippet = text[m.start() : m.end()][:80]
                banned_hits.append(f"{p}:{line_no}:{raw}:{snippet}")
    assert (
        not banned_hits
    ), "Banned tokens found (strict-mode violation):\n" + "\n".join(
        banned_hits
    )
