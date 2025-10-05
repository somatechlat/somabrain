import os

os.environ.setdefault("SOMABRAIN_STRICT_REAL_BYPASS", "1")

mem_endpoint = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
if mem_endpoint is not None:
    sanitized = mem_endpoint.strip()
    if sanitized:
        os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = sanitized
    else:
        os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = "http://127.0.0.1:9595"
else:
    os.environ.setdefault("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://127.0.0.1:9595")
