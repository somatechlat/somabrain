"""Module debug_e2e_manual."""

import os
import sys
import django
from django.conf import settings

# Setup Django (required for MemoryClient settings)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = "http://127.0.0.1:10101"
django.setup()

from somabrain.memory_client import MemoryClient

def run_debug():
    """Execute run debug.
        """

    print("DEBUG: Initializing MemoryClient...")
    client = MemoryClient(cfg=settings)
    
    try:
        url = client._transport.client.base_url
        print(f"DEBUG: Checking Health... Target: {url}")
    except:
        print("DEBUG: Checking Health... (URL Unknown)")
    try:
        health = client.health()
        print(f"DEBUG: Health Result: {health}")
    except Exception as e:
        print(f"ERROR: Health Check Failed: {e}")
        return

    test_key = "manual-debug-key"
    payload = {"key": test_key, "content": "Manual Debug Content"}

    print(f"DEBUG: Attempting Remember({test_key})...")
    try:
        coord = client.remember(coord_key=test_key, payload=payload)
        print(f"DEBUG: Remember Success. Coord: {coord}")
    except Exception as e:
        print(f"ERROR: Remember Failed: {e}")
        # We continue to see if Recall works (unlikely)

    print(f"DEBUG: Attempting Recall('Manual')...")
    try:
        hits = client.recall(query="Manual", top_k=1)
        print(f"DEBUG: Recall Hits: {hits}")
    except Exception as e:
        print(f"ERROR: Recall Failed: {e}")

if __name__ == "__main__":
    run_debug()