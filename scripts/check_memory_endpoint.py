import os
import sys
from common.config.settings import settings
import importlib
from common.logging import logger

#!/usr/bin/env python3
# ruff: noqa: E402

# Ensure we use the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Set env var to point at the host memory endpoint

os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = os.environ.get(
    "SOMABRAIN_MEMORY_HTTP_ENDPOINT", settings.memory_http_endpoint
)
# Clear somabrain modules to mimic fresh import like tests do
for m in list(sys.modules.keys()):
    if m.startswith("somabrain"):
        sys.modules.pop(m, None)


app_mod = importlib.import_module("somabrain.app")
print("Imported somabrain.app -> app object:", getattr(app_mod, "app", None))
# Access runtime mt_memory
try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
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
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        # try to inspect base_url attribute if httpx is used
        base = None
        if http_client is not None and hasattr(http_client, "base_url"):
            base = getattr(http_client, "base_url")
        elif async_client is not None and hasattr(async_client, "base_url"):
            base = getattr(async_client, "base_url")
        print("Resolved base_url:", base)
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise
except Exception as e:
    logger.exception("Exception caught: %s", e)
    raise

# Print environment info
print(
    "ENV SOMABRAIN_MEMORY_HTTP_ENDPOINT=",
    os.environ.get("SOMABRAIN_MEMORY_HTTP_ENDPOINT"), )
print("Running inside Docker? ", os.path.exists("/.dockerenv"))
print("Done.")
