"""
Status Report Generator for SomaBrain
=====================================

This small utility reads the *canonical roadmap* (``docs/CANONICAL_ROADMAP.md``) and
produces a concise console report showing which items are **completed**, **in
progress**, or **pending**.  It also cross‑checks the presence of the core
Phase‑1 autonomous modules (``Planner``, ``EmotionModel`` and
``CollaborationManager``) and reports whether they are importable.

Usage
-----
::

    $ source venv/bin/activate
    $ python examples/status_report.py

The script is deliberately lightweight – it does not depend on any third‑party
packages beyond the Python standard library.
"""

from __future__ import annotations

import re
import sys
from importlib import import_module
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Helper to parse the markdown roadmap
# ---------------------------------------------------------------------------


def _extract_items(section_text: str) -> List[Tuple[str, str]]:
    """Return a list of ``(status, description)`` tuples for a section.

    The roadmap uses the following markers:
    - ``✅`` – completed
    - ``⚠️`` or ``IN PROGRESS`` – in progress
    - ``❌`` or a plain ``-`` without a check – pending
    """
    items: List[Tuple[str, str]] = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        # Remove the leading dash and any whitespace
        content = line[1:].strip()
        # Detect explicit emoji markers
        if content.startswith("✅"):
            status = "COMPLETED"
            desc = content[1:].strip()
        elif content.startswith("⚠️") or "IN PROGRESS" in content.upper():
            status = "IN_PROGRESS"
            desc = re.sub(r"⚠️", "", content, flags=re.IGNORECASE).strip()
        else:
            # Anything else is considered pending
            status = "PENDING"
            desc = content
        # Strip any leading checkbox text like "[ ]" if present
        desc = re.sub(r"^\[.?\]\s*", "", desc)
        items.append((status, desc))
    return items


def parse_roadmap(path: Path) -> Dict[str, List[Tuple[str, str]]]:
    """Parse the markdown file and return a mapping of *section title* → items."""
    if not path.is_file():
        raise FileNotFoundError(f"Roadmap file not found: {path}")
    text = path.read_text(encoding="utf-8")
    sections: Dict[str, List[Tuple[str, str]]] = {}
    current_title = None
    buffer = []
    for line in text.splitlines():
        header_match = re.match(r"^##+\s+(.*)$", line)
        if header_match:
            # Save previous section
            if current_title:
                sections[current_title] = _extract_items("\n".join(buffer))
            current_title = header_match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    # Capture the last buffered section
    if current_title:
        sections[current_title] = _extract_items("\n".join(buffer))
    return sections


# ---------------------------------------------------------------------------
# Simple import‑check for core Phase‑1 cognitive classes
# ---------------------------------------------------------------------------


def _check_import(module_path: str, attr: str) -> bool:
    """Return ``True`` if *attr* can be imported from *module_path*."""
    try:
        mod = import_module(module_path)
        return hasattr(mod, attr)
    except Exception:
        return False


def check_core_cognitive_modules() -> Dict[str, bool]:
    """Verify that the three Phase‑1 cognitive classes are importable.

    Returns a mapping ``{class_name: bool}`` where ``True`` means the class is
    available in the current environment.
    """
    checks = {
        "Planner": _check_import("somabrain.cognitive.planning", "Planner"),
        "EmotionModel": _check_import("somabrain.cognitive.emotion", "EmotionModel"),
        "CollaborationManager": _check_import(
            "somabrain.cognitive.collaboration", "CollaborationManager"
        ),
    }
    return checks


# ---------------------------------------------------------------------------
# Pretty‑print helpers
# ---------------------------------------------------------------------------


def _print_section(title: str, items: List[Tuple[str, str]]) -> None:
    print(f"\n=== {title} ===")
    for status, desc in items:
        symbol = {
            "COMPLETED": "✅",
            "IN_PROGRESS": "⚠️",
            "PENDING": "❌",
        }.get(status, "❓")
        print(f"  {symbol} {desc} [{status}]")


def main() -> int:
    root = Path(__file__).resolve().parents[2]  # repository root
    roadmap_path = root / "docs" / "CANONICAL_ROADMAP.md"
    try:
        sections = parse_roadmap(roadmap_path)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    print("SomaBrain Project Status Report")
    print("================================")
    # Print the high‑level phases we care about
    for phase in [
        "Phase 1: Autonomous Operations",
        "Phase 2: Advanced Memory Management",
        "Phase 3: Enhanced Cognitive Capabilities",
    ]:
        items = sections.get(phase, [])
        if items:
            _print_section(phase, items)
        else:
            print(f"\n=== {phase} ===\n  (no items found)\n")

    # Core cognitive class availability
    print("\n=== Core Phase‑1 Cognitive Classes ===")
    core_checks = check_core_cognitive_modules()
    for name, available in core_checks.items():
        status = "✅ Available" if available else "❌ Missing"
        print(f"  {name}: {status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
