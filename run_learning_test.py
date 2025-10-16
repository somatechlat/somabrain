import os
import uuid
import time
import requests

# Use centralized configuration for consistent testing
try:
    from tests.test_config import SOMABRAIN_API_URL
    BASE = SOMABRAIN_API_URL
except ImportError:
    # Fallback for standalone usage
    BASE = os.getenv("SOMA_API_URL", "http://127.0.0.1:9696")


def _api_get(path):
    """TODO: Add docstring."""
    resp = requests.get(f"{BASE.rstrip('/')}/{path.lstrip('/')}", timeout=5)
    resp.raise_for_status()
    return resp.json()


def _api_post(path, json_body, headers=None):
    """TODO: Add docstring."""
    resp = requests.post(
        f"{BASE.rstrip('/')}/{path.lstrip('/')}",
        json=json_body,
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_adaptation_state():
    """TODO: Add docstring."""
    try:
        return _api_get("context/adaptation/state")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


def remember_memory():
    """TODO: Add docstring."""
    payload = {
        "coord": None,
        "payload": {
            "task": "learning-suite",
            "content": "learning test memory",
            "phase": "bootstrap",
            "quality_score": 0.9,
        },
    }
    return _api_post("remember", payload)


def evaluate(session_id, query, headers):
    """TODO: Add docstring."""
    return _api_post(
        "context/evaluate",
        {"session_id": session_id, "query": query, "top_k": 3},
        headers=headers,
    )


def submit_feedback(session_id, query, prompt, headers):
    """TODO: Add docstring."""
    payload = {
        "session_id": session_id,
        "query": query,
        "prompt": prompt,
        "response_text": "ack",
        "utility": 0.9,
        "reward": 0.9,
    }
    return _api_post("context/feedback", payload, headers=headers)


def main():
    """TODO: Add docstring."""
    before = get_adaptation_state()
    session_id = f"learning-{uuid.uuid4().hex[:16]}"
    headers = {"X-Model-Confidence": "8.5", "X-Session-ID": session_id}
    query = "measure my adaptation progress"
    remember_memory()
    eval_res = evaluate(session_id, query, headers)
    baseline_weights = list(eval_res.get("weights", []))
    iterations = 4
    for _ in range(iterations):
        prompt = eval_res.get("prompt")
        submit_feedback(session_id, query, prompt, headers)
        time.sleep(0.05)
        eval_res = evaluate(session_id, query, headers)
    after = get_adaptation_state()
    print("=== Adaptation State Before ===")
    print(before)
    print("=== Adaptation State After ===")
    print(after)
    if before and after:
        print(
            "Alpha delta:", after["retrieval"]["alpha"] - before["retrieval"]["alpha"]
        )
        print(
            "Lambda delta:", after["utility"]["lambda_"] - before["utility"]["lambda_"]
        )
    else:
        print("Could not retrieve adaptation state; checking weight change")
        final_weights = list(eval_res.get("weights", []))
        print("Baseline weights length", len(baseline_weights))
        print("Final weights length", len(final_weights))
        diffs = [abs(f - b) for f, b in zip(final_weights, baseline_weights)]
        print("Weight diffs (first 5):", diffs[:5])


if __name__ == "__main__":
    main()
