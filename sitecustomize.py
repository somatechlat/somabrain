import os

# Do NOT set SOMABRAIN_STRICT_REAL_BYPASS here. Developers should opt-in
# to bypassing strict-real mode explicitly when they understand the trade-offs.

mem_endpoint = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
if mem_endpoint is not None:
    sanitized = mem_endpoint.strip()
    if sanitized:
        os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = sanitized
    else:
        os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = "http://127.0.0.1:9595"
else:
    os.environ.setdefault("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://127.0.0.1:9595")
