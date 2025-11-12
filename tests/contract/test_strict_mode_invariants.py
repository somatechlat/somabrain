import os
import re
from pathlib import Path

import pytest


@pytest.mark.contract
def test_banned_keywords_absent():
    # Guardrail: ensure no accidental introduction of dev-only libs or bypass flags
    banned = [
        r"fakeredis",
        r"sqlite://",
        r"noop\s*tracer",
        r"disable_?auth",
        r"KafkaProducer\s*\(.*from\s+kafka",  # legacy kafka-python producer
    ]
    repo = Path(__file__).resolve().parents[2]
    code_dirs = [
        repo / "somabrain",
        repo / "services",
        repo / "common",
        repo / "observability",
    ]
    patterns = [re.compile(p, re.IGNORECASE) for p in banned]
    hits: list[tuple[str, int, str]] = []
    for root in code_dirs:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for pat in patterns:
                    if pat.search(line):
                        hits.append((str(path.relative_to(repo)), i, line.strip()))
                        break
    assert not hits, "Banned dev-only or legacy patterns found:\n" + "\n".join(
        f"{p}:{ln}: {s}" for p, ln, s in hits
    )


@pytest.mark.contract
def test_pytest_config_targets_tests_folder_only():
    repo = Path(__file__).resolve().parents[2]
    ini = (repo / "pytest.ini").read_text(encoding="utf-8")
    assert "testpaths = tests" in ini
