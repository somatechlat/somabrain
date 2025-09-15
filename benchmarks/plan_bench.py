"""
Planning Benchmark: Post-Persist Improvement
-------------------------------------------

Seeds a small set of tasks and relations, then compares the suggested plan
for a query key before and after a RAG session is persisted (which adds
query->session and session->doc edges). The planning phase includes the
relation type 'retrieved_with' to leverage the new edges.
"""

from __future__ import annotations

from typing import List

from fastapi.testclient import TestClient

from somabrain.app import app


def _remember(client: TestClient, task: str, headers: dict):
    r = client.post(
        "/remember",
        json={"payload": {"task": task, "memory_type": "episodic", "importance": 1}},
        headers=headers,
    )
    assert r.status_code == 200, r.text


def _link(
    client: TestClient,
    from_key: str,
    to_key: str,
    typ: str,
    headers: dict,
    weight: float = 1.0,
):
    r = client.post(
        "/link",
        json={"from_key": from_key, "to_key": to_key, "type": typ, "weight": weight},
        headers=headers,
    )
    assert r.status_code == 200, r.text


def _plan(
    client: TestClient,
    task_key: str,
    rel_types: List[str],
    headers: dict,
    max_steps: int = 5,
) -> List[str]:
    r = client.post(
        "/plan/suggest",
        json={"task_key": task_key, "max_steps": max_steps, "rel_types": rel_types},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json().get("plan", [])


def _hit_rate(items: List[str], truths: List[str]) -> float:
    if not truths:
        return 0.0
    s = set(items)
    return len([t for t in truths if t in s]) / float(len(truths))


def run():
    client = TestClient(app)
    headers = {"X-Tenant-ID": "planbench"}

    # Seed tasks/documents
    goal_docs = [
        "design solar array layout",
        "estimate battery capacity",
        "choose inverter size",
    ]
    for d in goal_docs:
        _remember(client, d, headers)

    # Add some structural relations among the docs to simulate knowledge
    _link(
        client,
        "design solar array layout",
        "choose inverter size",
        "depends_on",
        headers,
    )
    _link(
        client, "estimate battery capacity", "choose inverter size", "related", headers
    )

    query = "solar project planning"

    # Baseline plan suggestions without RAG session links
    base_plan = _plan(
        client,
        query,
        rel_types=["depends_on", "causes", "part_of", "motivates", "related"],
        headers=headers,
    )
    base_hr = _hit_rate(base_plan, goal_docs)

    # Persist a RAG session (vector + wm) to create query-linked edges
    r = client.post(
        "/rag/retrieve",
        headers=headers,
        json={
            "query": query,
            "top_k": 5,
            "retrievers": ["vector", "wm"],
            "persist": True,
        },
    )
    assert r.status_code == 200, r.text

    # Plan again including 'retrieved_with' to leverage RAG-created edges
    rich_plan = _plan(
        client,
        query,
        rel_types=["retrieved_with", "depends_on", "related"],
        headers=headers,
    )
    rich_hr = _hit_rate(rich_plan, goal_docs)

    print("Plan Bench Results")
    print(
        {
            "baseline_plan": base_plan,
            "baseline_hit_rate": base_hr,
            "post_persist_plan": rich_plan,
            "post_persist_hit_rate": rich_hr,
        }
    )


if __name__ == "__main__":
    run()
