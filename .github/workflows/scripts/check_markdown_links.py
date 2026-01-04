#!/usr/bin/env python3
"""Check markdown links in documentation."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DOCS = ROOT / "docs"

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def check_file(md_file):
    """Check all links in a markdown file."""
    errors = []
    content = md_file.read_text()

    for match in LINK_PATTERN.finditer(content):
        text, link = match.groups()

        # Skip external links
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue

        # Resolve relative path
        target = (md_file.parent / link).resolve()

        # Check if target exists
        if not target.exists():
            errors.append(f"{md_file.relative_to(ROOT)}: broken link [{text}]({link})")

    return errors


def main():
    """Check all markdown files."""
    all_errors = []

    for md_file in DOCS.rglob("*.md"):
        all_errors.extend(check_file(md_file))

    if all_errors:
        print("❌ Broken markdown links found:\n")
        for error in all_errors:
            print(f"  {error}")
        sys.exit(1)

    print("✓ All markdown links are valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
