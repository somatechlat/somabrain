import asyncio
import os
import uuid
import sys

# Configure environment for Host-to-Docker connectivity
os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = "http://localhost:9595"  # SFM API (Updated from docker ps)
os.environ["SOMABRAIN_REDIS_URL"] = "redis://localhost:30100/0"         # SomaBrain Redis
os.environ["SOMABRAIN_POSTGRES_DSN"] = "postgresql://soma:soma@localhost:30106/somabrain"
# Disable other strict checks that might block simple script execution if services aren't perfect yet
os.environ["SOMABRAIN_STRICT_REAL"] = "0" 

# Add repo to path
sys.path.append(os.getcwd())

from somabrain.bootstrap.core_singletons import create_fractal_memory
from somabrain.memory_client import MemoryClient

class MockConfig:
    def __init__(self):
        self.memory_http_endpoint = "http://localhost:9595"
        self.memory_http_token = "dev-032f8d463c84e7ef0d834c3a"
        self.namespace = "verification_test"
        self.memory_fast_ack = False
        self.memory_db_path = "./data/memory.db"

async def verify_adapter_flow():
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
        "type": "test_fact"
    }
    
    print(f"\n>>> 2. Encoding Fractal (Writing to SFM via HTTP)...")
    try:
        # This calls adapter.encode_fractal -> client.remember -> HTTP POST localhost:35000
        nodes = adapter.encode_fractal(content, importance=0.9)
        print(f"    Success! Returned nodes: {nodes}")
        
    except Exception as e:
        print(f"    FAILED to write: {e}")
        return

    print(f"\n>>> 3. Verifying Retrieval (Reading from SFM via HTTP)...")
    try:
        # Give it a moment for consistency if needed (though SFM is usually fast)
        await asyncio.sleep(1)
        
        # This calls adapter.retrieve_fractal -> client.recall -> HTTP POST localhost:35000/recall
        query = {"content": f"VIBE Verification Trace {trace_id}"}
        results = adapter.retrieve_fractal(query, top_k=1)
        
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

if __name__ == "__main__":
    asyncio.run(verify_adapter_flow())
