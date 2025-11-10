import os
import re
from pathlib import Path

# Phase 0 invariants: enforce Avro-only and modern Kafka client usage.
# Broader invariants (auth/redis/sqlite/tracing) will be enabled in Phase 0.2+.
BANNED_PATTERNS = [
    r"fallback to JSON",
    r"REWARD_FORCE_JSON",
    r"from kafka import KafkaProducer",
    r"from kafka import KafkaConsumer",
    r"fakeredis",
    r"SOMABRAIN_ALLOW_LOCAL_WM",
]

ALLOWED_EXCEPTIONS = {
    # Allow documentation references outside code paths (e.g., README) for clarity.
    "README.md": BANNED_PATTERNS,
    "ROADMAP_CANONICAL.md": BANNED_PATTERNS,
}

CODE_ROOT = Path(__file__).resolve().parents[2] / "somabrain"

def scan_file(path: Path):
    text = path.read_text(errors="ignore")
    violations = []
    for pat in BANNED_PATTERNS:
        if any(path.name == allow and re.search(pat, text) for allow in ALLOWED_EXCEPTIONS):
            continue
        if re.search(pat, text):
            violations.append(pat)
    return violations

def test_no_strict_mode_fallbacks():
    violations_total = []
    for p in CODE_ROOT.rglob("*.py"):
        # Skip virtual env or build artifacts if inside tree
        if "/.venv/" in str(p):
            continue
        # Skip schemas / generated code or tests referencing failure messages explicitly
        if p.name.endswith("_pb2.py") or p.name.endswith("_pb2.pyi"):
            continue
        v = scan_file(p)
        if v:
            violations_total.append((p, v))
    if violations_total:
        details = "\n".join(f"{path}: {', '.join(pats)}" for path, pats in violations_total)
        raise AssertionError(f"Strict-mode invariant violations detected:\n{details}")
