#!/usr/bin/env python3
"""Enforce clean project structure - prevent clutter regressions."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# Forbidden patterns that should never be committed
FORBIDDEN_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/.DS_Store",
    "**/*.swp",
    "**/*.swo",
    "**/*~",
    "**/*.bak",
    "**/*.orig",
    "**/*.rej",
    "**/ports.json",
    "**/ports.*.json",
    "**/*.egg-info",
]

# Forbidden files in root
FORBIDDEN_ROOT_FILES = [
    "=7",
    "somabrain.zip",
    ".DS_Store",
    "ports.json",
]

# Required documentation structure
REQUIRED_DOCS = [
    "docs/README.md",
    "docs/user-manual/index.md",
    "docs/technical-manual/index.md",
    "docs/development-manual/index.md",
    "docs/onboarding-manual/index.md",
]

# Forbidden documentation paths (removed in cleanup)
FORBIDDEN_DOCS = [
    "docs/CANONICAL_IMPROVEMENTS.md",
    "docs/DOCUMENTATION_GUIDE.md",
    "docs/vibe-coding-rules.md",
    "docs/cog-threads",
    "docs/RFCs",
    "docs/source",
    "docs/development-manual/architecture-decisions",
    "docs/development-manual/dual-cluster.md",
    "docs/development-manual/dual-stack.md",
    "docs/development-manual/era-of-experience.md",
    "docs/development-manual/learning-loop.md",
    "docs/onboarding-manual/checklists",
    "docs/onboarding-manual/environment-setup.md",
    "docs/onboarding-manual/resources",
    "docs/technical-manual/security/compliance-and-proofs.md",
    "docs/technical-manual/security/data-classification.md",
    "docs/technical-manual/security/strict-mode.md",
    "docs/monitoring/alertmanager-playbooks.md",
]

# Forbidden directories (removed in cleanup)
FORBIDDEN_DIRS = [
    "brain",
    "artifacts/learning",
]


def check_forbidden_patterns():
    """Check for forbidden file patterns."""
    errors = []
    for pattern in FORBIDDEN_PATTERNS:
        matches = list(ROOT.glob(pattern))
        if matches:
            errors.append(f"Found forbidden pattern '{pattern}':")
            for m in matches[:5]:
                errors.append(f"  - {m.relative_to(ROOT)}")
            if len(matches) > 5:
                errors.append(f"  ... and {len(matches) - 5} more")
    return errors


def check_forbidden_root_files():
    """Check for forbidden files in root."""
    errors = []
    for fname in FORBIDDEN_ROOT_FILES:
        fpath = ROOT / fname
        if fpath.exists():
            errors.append(f"Forbidden root file exists: {fname}")
    return errors


def check_required_docs():
    """Check required documentation exists."""
    errors = []
    for doc in REQUIRED_DOCS:
        if not (ROOT / doc).exists():
            errors.append(f"Required documentation missing: {doc}")
    return errors


def check_forbidden_docs():
    """Check forbidden documentation paths don't exist."""
    errors = []
    for doc in FORBIDDEN_DOCS:
        path = ROOT / doc
        if path.exists():
            errors.append(f"Forbidden documentation exists: {doc}")
    return errors


def check_forbidden_dirs():
    """Check forbidden directories don't exist."""
    errors = []
    for dirname in FORBIDDEN_DIRS:
        path = ROOT / dirname
        if path.exists():
            errors.append(f"Forbidden directory exists: {dirname}")
    return errors


def main():
    """Run all structure checks."""
    all_errors = []
    
    all_errors.extend(check_forbidden_patterns())
    all_errors.extend(check_forbidden_root_files())
    all_errors.extend(check_required_docs())
    all_errors.extend(check_forbidden_docs())
    all_errors.extend(check_forbidden_dirs())
    
    if all_errors:
        print("❌ Project structure violations found:\n")
        for error in all_errors:
            print(f"  {error}")
        print("\nRun cleanup: rm -rf .mypy_cache .ruff_cache __pycache__")
        sys.exit(1)
    
    print("✓ Project structure is clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
