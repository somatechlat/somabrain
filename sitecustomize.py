import os

# Do NOT set SOMABRAIN_ALLOW_BACKEND_FALLBACKS here. Developers should opt-in
# to bypassing backend enforcement explicitly when they understand the trade-offs.

mem_endpoint = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
if mem_endpoint is not None:
    sanitized = mem_endpoint.strip()
    if sanitized:
        os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = sanitized
    else:
        # leave unset to let central settings or docker compose define defaults
        os.environ.pop("SOMABRAIN_MEMORY_HTTP_ENDPOINT", None)
