"""Generate a learning curve plot by exercising the live SomaBrain API."""

from __future__ import annotations

import os
import pathlib
import time
import uuid
from typing import Dict, List

import matplotlib.pyplot as plt
import requests

BASE_URL = os.getenv("SOMA_API_URL", "http://127.0.0.1:9696").rstrip("/")
OUTPUT_PATH = pathlib.Path("artifacts/plots/learning_curve.png")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

TENANT_HEADERS: Dict[str, str] = {
    "X-Model-Confidence": "8.5",
}


def _get(path: str) -> requests.Response:
    resp = requests.get(f"{BASE_URL}/{path.lstrip('/')}", timeout=5)
    resp.raise_for_status()
    return resp


def _post(path: str, payload: dict, headers: Dict[str, str] | None = None) -> requests.Response:
    resp = requests.post(
        f"{BASE_URL}/{path.lstrip('/')}",
        json=payload,
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp


def fetch_adaptation_state() -> dict:
    return _get("context/adaptation/state").json()


def prime_memory() -> None:
    payload = {
        "coord": None,
        "payload": {
            "task": "learning-suite",
            "content": "learning test memory",
            "phase": "bootstrap",
            "quality_score": 0.9,
        },
    }
    _post("remember", payload)


def run_learning_iterations(iterations: int = 6) -> dict:
    session_id = f"learn-{uuid.uuid4().hex[:16]}"
    headers = {**TENANT_HEADERS, "X-Session-ID": session_id}
    query = "measure my adaptation progress"

    eval_payload = {"session_id": session_id, "query": query, "top_k": 3}
    eval_resp = _post("context/evaluate", eval_payload, headers=headers).json()

    lambda_vals: List[float] = []
    alpha_vals: List[float] = []
    history: List[int] = []

    def record_state(state: dict) -> None:
        lambda_vals.append(state["utility"]["lambda_"])
        alpha_vals.append(state["retrieval"]["alpha"])
        history.append(state.get("history_len", 0))

    record_state(fetch_adaptation_state())

    for _ in range(iterations):
        prompt = eval_resp.get("prompt")
        feedback_payload = {
            "session_id": session_id,
            "query": query,
            "prompt": prompt,
            "response_text": "ack",
            "utility": 0.9,
            "reward": 0.9,
        }
        _post("context/feedback", feedback_payload, headers=headers)
        time.sleep(0.05)
        state = fetch_adaptation_state()
        record_state(state)
        eval_resp = _post("context/evaluate", eval_payload, headers=headers).json()

    return {
        "iterations": list(range(len(lambda_vals))),
        "lambda": lambda_vals,
        "alpha": alpha_vals,
        "history": history,
    }


def plot_learning_curves(data: dict) -> pathlib.Path:
    plt.figure(figsize=(8, 4.5))
    plt.plot(data["iterations"], data["lambda"], marker="o", label="Utility lambda")
    plt.plot(data["iterations"], data["alpha"], marker="s", label="Retrieval alpha")
    plt.xlabel("Feedback Iteration")
    plt.ylabel("Weight Value")
    plt.title("SomaBrain Online Adaptation Progress")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=160)
    plt.close()
    return OUTPUT_PATH


def main() -> pathlib.Path:
    prime_memory()
    data = run_learning_iterations()
    return plot_learning_curves(data)


if __name__ == "__main__":
    path = main()
    print(f"Learning curve written to {path}")
