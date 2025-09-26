"""Quickstart: verify the external memory service HTTP endpoint.

This example intentionally does not import any vendor-specific memory package.
The Brain treats the memory service as an external HTTP API only. The script
probes the configured endpoint (default http://localhost:9595) and prints health
information.
"""

import os
import sys

try:
    import requests
except Exception:
    print("The 'requests' library is required to run this example. Install with: pip install requests")
    sys.exit(1)


def main():
    endpoint = os.environ.get("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:9595")
    try:
        r = requests.get(f"{endpoint.rstrip('/')}/health", timeout=3.0)
        print("Memory service health status:", r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text)
    except Exception as e:
        print("Failed to contact memory service at", endpoint, "->", e)


if __name__ == "__main__":
    main()
