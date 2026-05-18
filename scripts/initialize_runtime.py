#!/usr/bin/env python3
"""Initialize runtime singletons for SomaBrain."""

from __future__ import annotations

import sys
import traceback


def main() -> int:
    """Initialize runtime singletons and fail loudly on partial startup."""
    sys.path.insert(0, "/app")

    import django

    django.setup()

    from somabrain.runtime.manager import initialize_runtime

    status = initialize_runtime()
    print(f"initialize_runtime: status={status}")

    failed = [name for name, ok in status.items() if not ok]
    if failed:
        raise RuntimeError(
            "Runtime initialization incomplete: " + ", ".join(sorted(failed))
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(
            "initialize_runtime: failed to initialize runtime:\n",
            traceback.format_exc(),
        )
        raise
