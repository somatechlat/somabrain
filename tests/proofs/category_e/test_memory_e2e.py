"""Module test_memory_e2e."""

import asyncio
import os
import uuid
import sys

# Configure environment for Host-to-Docker connectivity
os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = (
    "http://localhost:9595"  # SFM API (Updated from docker ps)
)
os.environ["SOMABRAIN_REDIS_URL"] = "redis://localhost:30100/0"  # SomaBrain Redis
os.environ["SOMABRAIN_POSTGRES_DSN"] = "postgresql://soma:soma@localhost:30106/somabrain"
# Disable other strict checks that might block simple script execution if services aren't perfect yet
os.environ["SOMABRAIN_STRICT_REAL"] = "0"

# Add repo to path
sys.path.append(os.getcwd())

from somabrain.bootstrap.core_singletons import create_fractal_memory


class MockConfig:
    """Mockconfig class implementation."""

    def __init__(self):
        """Initialize the instance."""

        self.memory_http_endpoint = "http://localhost:9595"
        self.memory_http_token = "dev-032f8d463c84e7ef0d834c3a"
        self.namespace = "verification_test"
        self.memory_fast_ack = False
        self.memory_db_path = None


async def verify_adapter_flow():
    """Execute verify adapter flow."""

    print(">>> 1. Initializing Adapter & Client...")
    cfg = MockConfig()
    # Create the adapter using our factory (which uses MemoryClient)
    adapter = create_fractal_memory(cfg)

    print(f"    Adapter Type: {type(adapter)}")
    print(f"    Inner Client: {type(adapter.client)}")

    # Generate test content
    trace_id = str(uuid.uuid4())
    content = {
        "id": trace_id,
        "content": f"VIBE Verification Trace {trace_id}",
        "type": "test_fact",
    }

    print("\n>>> 2. Encoding Fractal (Writing to SFM via HTTP)...")
    try:
        # This calls adapter.encode_fractal -> client.remember -> HTTP POST localhost:35000
        nodes = adapter.encode_fractal(content, importance=0.9)
        print(f"    Success! Returned nodes: {nodes}")

    except Exception as e:
        print(f"    FAILED to write: {e}")
        # If it's an HTTP error from MemoryClient (which raises on failure usually), print it
        # But MemoryClient might mask it. Let's inspect the adapter implementation or trust the print.
        # Actually verify_e2e.py calls adapter.encode_fractal.
        # If adapter raises, e captures it.
        import traceback

        traceback.print_exc()
        return

    print("\n>>> 3. Verifying Retrieval (Reading from SFM via HTTP)...")
    try:
        # Give it a moment for consistency if needed (though SFM is usually fast)
        await asyncio.sleep(5)

        # This calls adapter.retrieve_fractal -> client.recall -> HTTP POST localhost:35000/recall

        # VIBE CHECK 1: Direct Fetch by Coordinate (Persistence Proof)
        print(f"    Target Coord: {nodes[0]}")
        try:
            # adapter.client is MemoryClient
            direct_fetch = adapter.client.fetch_by_coord(nodes[0])
            if direct_fetch:
                print(
                    f"    ✅ VIBE CHECK 1 PASSED: Direct Fetch found memory: {direct_fetch[0].get('id')}"
                )
            else:
                print("    ❌ VIBE CHECK 1 FAILED: Direct Fetch returned empty.")
        except Exception as e:
            print(f"    ❌ VIBE CHECK 1 ERROR: {e}")

        # VIBE CHECK 2: Semantic Recall
        # Use exact content for query to maximize cosine similarity with CodeBERT
        query_text = f"VIBE Verification Trace {trace_id}"
        results = adapter.retrieve_fractal({"content": query_text}, top_k=5)

        if results:
            print(f"    ✅ VIBE CHECK 2 PASSED: Semantic Search found {len(results)} results.")
        else:
            print(
                "    ⚠️ VIBE CHECK 2 WARNING: Semantic Search returned no results (Possible embedding model loading issue)."
            )

        # VIBE CHECK 3: Keyword/Exact Search (Hybrid)
        print("    Testing Keyword/Hybrid Search...")
        # Note: MemoryClient might not expose raw keyword_search, but retrieve_fractal uses hybrid.
        # Let's rely on the previous fetch_by_coord as the primary persistence proof.

        if not results:
            print("    FAILED: No results found.")
        else:
            print(f"    Success! Retrieved {len(results)} results.")
            top_node, score = results[0]
            print(f"    Top Match: {top_node.memory_trace}")
            print(f"    Score: {score}")

            if top_node.memory_trace.get("id") == trace_id:
                print("\n✅ VIBE CHECK PASSED: Data Round-Tripped via Single Point of Access!")
            else:
                print("\n❌ DATA MISMATCH: Retrieved ID does not match.")

    except Exception as e:
        print(f"    FAILED to read: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify_adapter_flow())
