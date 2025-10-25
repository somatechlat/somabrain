#!/usr/bin/env python3
"""Start Uvicorn after initializing SomaBrain runtime singletons in-process.

This ensures that the same Python process that runs Uvicorn has the runtime
singletons initialized, avoiding import-time backend-enforcement failures.
"""
import os
import sys
import uvicorn

# Ensure /app is on sys.path for imports
sys.path.insert(0, "/app")

HOST = os.getenv("SOMABRAIN_HOST", "0.0.0.0")
# Be resilient to empty or invalid env values
def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        if raw is None:
            return default
        raw = str(raw).strip()
        if raw == "":
            return default
        return int(raw)
    except Exception:
        return default

PORT = _int_env("SOMABRAIN_PORT", 9696)
WORKERS = _int_env("SOMABRAIN_WORKERS", 1)

try:
    # Run the initializer (idempotent)
    init_path = os.path.join(os.path.dirname(__file__), "initialize_runtime.py")
    if os.path.exists(init_path):
        # Execute initializer in this process so side-effects persist
        with open(init_path, "rb") as f:
            code = compile(f.read(), init_path, "exec")
            exec(code, {"__name__": "__main__"})
except Exception as e:
    print("start_server: initializer failed:\n", e)

# Use programmatic Uvicorn run so imports happen in this process

if WORKERS != 1:
    print("Warning: WORKERS != 1. For backend enforcement, workers should be 1 so runtime singletons are initialized in-process. Overriding WORKERS=1.")

# Use programmatic Server to avoid uvicorn spawning worker subprocesses that
# would not inherit the initialized singletons in this parent process.
config = uvicorn.Config("somabrain.app:app", host=HOST, port=PORT, workers=1)
server = uvicorn.Server(config)
server.run()
