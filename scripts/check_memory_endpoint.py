#!/usr/bin/env python3
# ruff: noqa: E402
import os
import sys

# Ensure we use the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Set env var to point at the host memory endpoint
from common.config.settings import settings
os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = os.environ.get(
    "SOMABRAIN_MEMORY_HTTP_ENDPOINT", settings.memory_http_endpoint
)
# Clear somabrain modules to mimic fresh import like tests do
for m in list(sys.modules.keys()):
    if m.startswith("somabrain"):
        sys.modules.pop(m, None)

import importlib

app_mod = importlib.import_module("somabrain.app")
print("Imported somabrain.app -> app object:", getattr(app_mod, "app", None))
# Access runtime mt_memory
try:
    mt_memory = getattr(app_mod, "mt_memory")
    print("mt_memory present:", mt_memory is not None)
    client = mt_memory.for_namespace("public")
    print(
        "Created MemoryClient, cfg.namespace=", getattr(client.cfg, "namespace", None)
    )
    http_client = getattr(client, "_http", None)
    async_client = getattr(client, "_http_async", None)
    print("_http client:", type(http_client), "truthy=", bool(http_client))
    print("_http_async client:", type(async_client), "truthy=", bool(async_client))
    try:
        # try to inspect base_url attribute if httpx is used
        base = None
        if http_client is not None and hasattr(http_client, "base_url"):
            base = getattr(http_client, "base_url")
        elif async_client is not None and hasattr(async_client, "base_url"):
            base = getattr(async_client, "base_url")
        print("Resolved base_url:", base)
    except Exception as e:
        print("Could not read base_url:", e)
except Exception as e:
    print("Error accessing mt_memory or creating client:", e)

# Print environment info
print(
    "ENV SOMABRAIN_MEMORY_HTTP_ENDPOINT=",
    os.environ.get("SOMABRAIN_MEMORY_HTTP_ENDPOINT"),
)
print("Running inside Docker? ", os.path.exists("/.dockerenv"))
print("Done.")
