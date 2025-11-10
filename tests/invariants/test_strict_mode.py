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
SERVICES_ROOT = CODE_ROOT / "services"
MONITORING_ROOT = CODE_ROOT / "monitoring"

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


def _scan_for_json_serialization(root: Path):
    patterns = [r"\bjson\.dumps\(", r"\borjson\.dumps\("]
    violations = []
    for p in root.rglob("*.py"):
        # Skip generated, tests, and obvious configuration or CLI helpers
        s = str(p)
        if any(seg in s for seg in ["/__pycache__/", "/tests/", "/_pb2.py", "/_pb2.pyi"]):
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if re.search(pat, text):
                violations.append((p, pat))
    return violations


def test_no_json_serialization_in_services():
    """Disallow raw JSON serialization in service/monitoring code paths.

    Avro-only posture: producers and processors must not use json.dumps/orjson.dumps
    for event payloads. If JSON is required for HTTP responses or logging, place code
    outside services/monitoring or use structured logging helpers.
    """
    violations = []
    for root in [SERVICES_ROOT, MONITORING_ROOT]:
        if root.exists():
            violations.extend(_scan_for_json_serialization(root))
    if violations:
        details = "\n".join(f"{path}: {pat}" for path, pat in violations)
        raise AssertionError(
            "JSON serialization found in services/monitoring code paths (Avro-only required):\n"
            + details
        )
