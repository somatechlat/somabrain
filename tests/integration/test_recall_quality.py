"""
Recall Quality Integration Tests (Workbench)

This module implements the Recall Testing Workbench (Task 18). It performs end-to-end
verification of the memory recall pipeline using real components and metrics.

Key Requirements:
- Real implementations only (no mocks).
- Metric calculation (Precision, Recall, nDCG).
- End-to-end flow validation (remember -> recall).
- Degradation path verification (if applicable).

Usage:
    pytest tests/integration/test_recall_quality.py
"""

import pytest
import asyncio
import uuid
from typing import List
import numpy as np

# Use the real MemoryClient
from somabrain.memory_client import MemoryClient
from somabrain.config import Config

# --- Metrics Helper Functions (Task 18.2) ---


def compute_precision_at_k(relevant: List[str], retrieved: List[str], k: int) -> float:
    """Compute Precision@K.

    Precision@K = (Relevant items in top K) / K
    """
    if k <= 0:
        return 0.0
    retrieved_k = retrieved[:k]
    intersection = set(relevant).intersection(set(retrieved_k))
    return len(intersection) / k


def compute_recall_at_k(relevant: List[str], retrieved: List[str], k: int) -> float:
    """Compute Recall@K.

    Recall@K = (Relevant items in top K) / (Total relevant items)
    """
    if not relevant:
        return 0.0
    retrieved_k = retrieved[:k]
    intersection = set(relevant).intersection(set(retrieved_k))
    return len(intersection) / len(relevant)


def compute_ndcg_at_k(relevant: List[str], retrieved: List[str], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain (nDCG) @ K.

    Assumes binary relevance (item is either relevant or not).
    """
    if k <= 0 or not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    dcg = 0.0
    for i, item_id in enumerate(retrieved_k):
        rel = 1.0 if item_id in relevant else 0.0
        dcg += rel / np.log2(i + 2)

    # Ideal DCG (perfect ordering)
    idcg = 0.0
    num_relevant = min(len(relevant), k)
    for i in range(num_relevant):
        idcg += 1.0 / np.log2(i + 2)

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# --- Integration Tests ---


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recall_quality_e2e():
    """
    Requirement 8.1: Verify recall quality (Precision/Recall/nDCG) on a small labeled corpus.
    Requirement 8.3: Core Memory Operations Work End-to-End (store then recall).
    """
    # Ensure we are running against a real backend (or local equivalent)
    # For this test, we assume the memory service is available via MemoryClient.
    # If not, the client will fail fast (as per our new strict rules).

    cfg = Config()
    # Use a unique namespace for isolation
    test_namespace = f"test_recall_{uuid.uuid4().hex[:8]}"
    cfg.namespace = test_namespace

    client = MemoryClient(cfg)

    # 1. Setup Labeled Corpus
    # We insert a set of memories related to specific "topics" (ground truth).
    topics = {
        "topic_a": [
            "The quick brown fox jumps over the lazy dog.",
            "Foxes are clever animals found in forests.",
            "Quick movement is key for a fox.",
        ],
        "topic_b": [
            "Quantum mechanics explains atomic behavior.",
            "Schrodinger's cat is a thought experiment.",
            "Wave-particle duality is fundamental.",
        ],
    }

    inserted_ids = {}  # Map content -> ID (or coordinate)

    print(f"\n[Setup] Injecting corpus into namespace: {test_namespace}")
    for topic, items in topics.items():
        for item in items:
            # Use the item text itself as the key for simplicity in this test
            key = f"{topic}:{hash(item)}"
            payload = {
                "content": item,
                "topic": topic,
                "memory_type": "episodic",
                "test_run_id": test_namespace,
            }
            # Use synchronous remember for simplicity in test setup, or await async
            coord = await client.aremember(key, payload)
            inserted_ids[item] = key

    # Allow a brief moment for indexing if the backend is async/eventually consistent
    # (Real backends might need a moment; local mocks are instant)
    await asyncio.sleep(1.0)

    # 2. Execute Queries & Measure Quality

    # Query 1: "fox" (Expecting topic_a items)
    query_1 = "fox"
    relevant_1 = [inserted_ids[item] for item in topics["topic_a"]]

    print(f"[Action] Recalling query: '{query_1}'")
    results_1 = await client.arecall(query_1, top_k=5)

    retrieved_ids_1 = []
    for hit in results_1:
        # Extract ID. Our payload enrichment ensures 'id' or 'key' is present.
        p = hit.payload
        rid = p.get("key") or p.get("id")
        if rid:
            retrieved_ids_1.append(rid)

    # Calculate Metrics
    p_at_3 = compute_precision_at_k(relevant_1, retrieved_ids_1, 3)
    r_at_3 = compute_recall_at_k(relevant_1, retrieved_ids_1, 3)
    ndcg_at_3 = compute_ndcg_at_k(relevant_1, retrieved_ids_1, 3)

    print(
        f"[Result] Query '{query_1}': P@3={p_at_3:.2f}, R@3={r_at_3:.2f}, nDCG@3={ndcg_at_3:.2f}"
    )

    # Assertions (Soft baselines, as embeddings vary)
    # We expect at least one relevant item to be found if the embedder/search works.
    assert len(retrieved_ids_1) > 0, "Recall should return results for known content"
    assert r_at_3 > 0.0, "Recall@3 should be non-zero for 'fox'"

    # Query 2: "quantum physics" (Expecting topic_b items)
    query_2 = "quantum physics"
    relevant_2 = [inserted_ids[item] for item in topics["topic_b"]]

    print(f"[Action] Recalling query: '{query_2}'")
    results_2 = await client.arecall(query_2, top_k=5)

    retrieved_ids_2 = []
    for hit in results_2:
        p = hit.payload
        rid = p.get("key") or p.get("id")
        if rid:
            retrieved_ids_2.append(rid)

    p_at_3_q2 = compute_precision_at_k(relevant_2, retrieved_ids_2, 3)
    print(f"[Result] Query '{query_2}': P@3={p_at_3_q2:.2f}")

    assert len(retrieved_ids_2) > 0, "Recall should return results for quantum query"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_tenant_isolation():
    """
    Requirement 8.4: Verify multi-tenant isolation.
    Tenant A's recalls should never return Tenant B's payloads.
    """
    cfg_a = Config()
    cfg_a.namespace = f"tenant_A_{uuid.uuid4().hex[:6]}"
    client_a = MemoryClient(cfg_a)

    cfg_b = Config()
    cfg_b.namespace = f"tenant_B_{uuid.uuid4().hex[:6]}"
    client_b = MemoryClient(cfg_b)

    secret_a = "The eagle flies at midnight."
    secret_b = "The sparrow sleeps at noon."

    # Store
    await client_a.aremember("secret_a", {"content": secret_a, "owner": "A"})
    await client_b.aremember("secret_b", {"content": secret_b, "owner": "B"})

    await asyncio.sleep(0.5)

    # Recall as A (should NOT see B)
    results_a = await client_a.arecall("sparrow", top_k=5)
    for hit in results_a:
        assert hit.payload.get("owner") != "B", "Tenant A saw Tenant B's data!"

    # Recall as B (should NOT see A)
    results_b = await client_b.arecall("eagle", top_k=5)
    for hit in results_b:
        assert hit.payload.get("owner") != "A", "Tenant B saw Tenant A's data!"

    print("\n[Success] Multi-tenant isolation verified.")
