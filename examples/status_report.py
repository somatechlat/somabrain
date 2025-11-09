"""SomaBrain documentation and math status checker."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict

# Project root sits one level above the examples/ directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOCS: Dict[str, Path] = {
    "Architecture": ROOT / "docs" / "architecture" / "somabrain-3.0.md",
    "Strict Mode": ROOT / "docs" / "architecture" / "STRICT_MODE.md",
    "BHDC Math": ROOT / "docs" / "architecture" / "math" / "bhdc-binding.md",
    "Density Matrix": ROOT / "docs" / "architecture" / "math" / "density-matrix.md",
    "REST API": ROOT / "docs" / "api" / "rest.md",
    "Operations Runbook": ROOT / "docs" / "operations" / "runbook.md",
    "Configuration": ROOT / "docs" / "operations" / "configuration.md",
    "Changelog": ROOT / "docs" / "releases" / "changelog.md",
}

MODULES: Dict[str, tuple[str, str]] = {
    "QuantumLayer": ("somabrain.quantum", "QuantumLayer"),
    "FDSalienceSketch": ("somabrain.salience", "FDSalienceSketch"),
    "UnifiedScorer": ("somabrain.scoring", "UnifiedScorer"),
    "DensityMatrix": ("memory.density", "DensityMatrix"),
}


def check_docs() -> Dict[str, bool]:
    """Return a mapping of document label to availability."""
    return {name: path.is_file() for name, path in DOCS.items()}


def check_modules() -> Dict[str, bool]:
    """Return a mapping of module label to import success."""
    results: Dict[str, bool] = {}
    for label, (module, attr) in MODULES.items():
        try:
            mod = importlib.import_module(module)
            results[label] = hasattr(mod, attr)
        except Exception:
            results[label] = False
    return results


def render_table(title: str, status: Dict[str, bool]) -> None:
    print(title)
    print("=" * len(title))
    for name, ok in status.items():
        icon = "[OK]" if ok else "[FAIL]"
        state = "ready" if ok else "missing"
        print(f"  {icon} {name}: {state}")


def main() -> int:
    doc_status = check_docs()
    module_status = check_modules()

    render_table("SomaBrain Documentation", doc_status)
    print()
    render_table("Core Math Modules", module_status)

    if not all(doc_status.values()):
        missing = [name for name, exists in doc_status.items() if not exists]
        print("\nMissing documentation entries:", ", ".join(missing), file=sys.stderr)
        return 1

    if not all(module_status.values()):
        failing = [name for name, ok in module_status.items() if not ok]
        print("\nModules failing import:", ", ".join(failing), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
