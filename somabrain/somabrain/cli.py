from __future__ import annotations

import os
import sys


def run_api() -> None:
    """Console entry: launch FastAPI app via uvicorn.

    Usage: somabrain-api [--host 0.0.0.0 --port 8000]
    Environment variables are respected (e.g., SOMABRAIN_* config).
    """
    try:
        import uvicorn  # type: ignore
    except Exception as e:
        print("uvicorn is required to run the API (pip install uvicorn)", file=sys.stderr)
        raise
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("somabrain.app:app", host=host, port=port, reload=False)

