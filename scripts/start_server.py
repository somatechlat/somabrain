#!/usr/bin/env python3
"""Start Uvicorn after initializing SomaBrain runtime singletons in-process.

This ensures that the same Python process that runs Uvicorn has the runtime
singletons initialized, avoiding import-time backend-enforcement failures.
"""
from common.config.settings import settings
import sys
import os
import uvicorn
import yaml
import logging.config

# Ensure /app is on sys.path for imports
sys.path.insert(0, "/app")

HOST = settings.host


# Prefer centralized Settings for numeric process configuration.
# Settings.port is stored as a string to support URL construction; coerce here safely.
def _coerce_int(value: str | int | None, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


PORT = _coerce_int(getattr(settings, "port", None), 9696)
WORKERS = _coerce_int(getattr(settings, "workers", None), 1)

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
    print(
        "Warning: WORKERS != 1. For backend enforcement, workers should be 1 so runtime singletons are initialized in-process. Overriding WORKERS=1."
    )

# Apply optional logging config if provided
LOG_CONFIG = settings.log_config
if os.path.exists(LOG_CONFIG):
    try:
        with open(LOG_CONFIG, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        logging.config.dictConfig(cfg)
    except Exception as e:
        print("start_server: failed to apply logging config:", e)

# Use programmatic Server to avoid uvicorn spawning worker subprocesses that would
# not inherit the initialized singletons in this parent process.
config = uvicorn.Config(
    "somabrain.app:app", host=HOST, port=PORT, workers=1, log_config=None
)
server = uvicorn.Server(config)
server.run()
