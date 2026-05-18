import os
import sys
import time
import requests
import uuid

# Configuration
BRAIN_HOST = os.getenv("SOMABRAIN_HOST", "localhost")
BRAIN_PORT = int(os.getenv("SOMABRAIN_PORT", "30101"))
ENDPOINT = f"http://{BRAIN_HOST}:{BRAIN_PORT}/api/memory"
TOKEN = os.getenv("SOMABRAIN_API_TOKEN", os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN", ""))

# Test Data
TEST_NAMESPACE = "bridge_verification"
TEST_CONTENT = f"Bridge verification test content {uuid.uuid4()}"

headers = {
    # SomaBrain might require different auth headers depending on configuration
    # For now, we assume it's using the standard pattern or no auth for internal testing if configured that way
    # But based on previous files, it seems to expect X-Tenant-ID
    "X-Tenant-ID": "public",
    "Content-Type": "application/json",
}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"


def verify_bridge():
    print(f"--- SOMA BRAIN -> SFM BRIDGE VERIFICATION | {time.ctime()} ---")
    print(f"Target: {ENDPOINT}")

    # 1. Store Memory via Brain
    print(f"Storing memory via Brain: '{TEST_CONTENT}'...")
    store_payload = {
        "content": TEST_CONTENT,
        "memory_type": "episodic",
        "metadata": {"origin": "bridge_verification", "vibe": "sovereign"},
    }

    try:
        # endpoint might be /remember based on test_resilience.py
        url = f"{ENDPOINT}/remember"
        print(f"POST {url}")
        r = requests.post(url, headers=headers, json=store_payload, timeout=10)
        print(f"Response: {r.status_code} {r.text}")
        r.raise_for_status()
        print("STORE OPERATION SUCCESSFUL")
    except Exception as e:
        print(f"STORE FAILED: {e}")
        sys.exit(1)

    # 2. Recall Memory via Brain
    print("Recalling memory via Brain...")
    recall_payload = {"query": "Bridge verification", "k": 1, "memory_type": "episodic"}

    try:
        # endpoint might be /recall
        url = f"{ENDPOINT}/recall"
        print(f"POST {url}")
        r = requests.post(url, headers=headers, json=recall_payload, timeout=10)
        print(f"Response: {r.status_code} {r.text}")
        r.raise_for_status()

        data = r.json()
        # Verify content matches
        # results structure depends on API, usually 'results' or 'memories'
        results = data.get("results", []) or data.get("memories", [])

        found = False
        for mem in results:
            if TEST_CONTENT in str(mem):
                found = True
                break

        if found:
            print("RECALL SUCCESS: Content match confirmed.")
            print("--- BRIDGE VERIFICATION COMPLETE | STATUS: OPERATIONAL ---")
        else:
            print(f"RECALL WARNING: Content not found in top 1 results. Got: {results}")
            # We don't exit 1 here necessarily as it might be an embedding delay/refresh issue
            # But for a proof it's good to be strict.
            # Let's retry once after sleep
            print("Retrying recall in 2 seconds...")
            time.sleep(2)
            r = requests.post(url, headers=headers, json=recall_payload, timeout=10)
            data = r.json()
            results = data.get("results", []) or data.get("memories", [])
            for mem in results:
                if TEST_CONTENT in str(mem):
                    print("RECALL SUCCESS (After Retry): Content match confirmed.")
                    print("--- BRIDGE VERIFICATION COMPLETE | STATUS: OPERATIONAL ---")
                    sys.exit(0)

            print("RECALL FAILED: Content still not found.")
            sys.exit(1)

    except Exception as e:
        print(f"RECALL FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Wait for service to be healthy first
    print("Checking Brain health...")
    try:
        r = requests.get(f"http://{BRAIN_HOST}:{BRAIN_PORT}/health", timeout=5)
        if r.status_code == 200:
            print("Brain is HEALTHY.")
        else:
            print(f"Brain health check returned {r.status_code}")
    except Exception as e:
        print(f"Brain health check failed: {e}")
        print("Proceeding anyway to force check...")

    verify_bridge()
