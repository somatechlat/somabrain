"""Regression suite for strict-real memory behavior.

These tests target the live SomaBrain API (port 9696 or cluster ingress). They
capture the current recall mismatch where `/recall` returns stale content even
when `/remember` succeeds. The test intentionally fails until the underlying
bug is resolved, giving us a deterministic guardrail.
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_recall_returns_latest_payload(client):
    """Store a payload and assert the newest content is surfaced first.

    Expected behavior: `/recall` should return the memory written most recently
    with matching task/query content. Current behavior returns stale data,
    causing this test to fail until the bug is fixed.
    """

    query = "truth-regression"
    stale_payload = {
        "task": query,
        "content": "legacy content",
        "importance": 0.1,
    }
    fresh_payload = {
        "task": query,
        "content": f"fresh content {uuid.uuid4()}",
        "importance": 0.9,
    }

    # Seed the stale entry to match observed production conditions.
    stale_resp = await client.post("/remember", json=stale_payload)
    assert stale_resp.status_code == 200

    # Write the new memory we expect to recall.
    fresh_resp = await client.post("/remember", json=fresh_payload)
    assert fresh_resp.status_code == 200

    recall_resp = await client.post("/recall", json={"query": query})
    assert recall_resp.status_code == 200
    data = recall_resp.json()
    results = data.get("results", [])
    assert results, "Recall returned no results"
    top = results[0]
    assert top.get("content") == fresh_payload["content"], (
        "Recall returned stale content; regression remains."
    )