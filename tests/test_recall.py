"""Integration test for basic recall functionality.

The test uses the ``client`` fixture defined in ``tests/conftest.py`` which
creates an ``httpx.AsyncClient`` pointing at the SomaBrain API. By setting the
environment variables ``SOMABRAIN_USE_LIVE_STACK=1`` and ``DISABLE_START_SERVER=1``
the fixture will target the already‑running server on port 9696 and will not
attempt to launch a secondary uvicorn instance.

The test performs a simple round‑trip:
1. POST a memory via ``/remember``.
2. GET a recall via ``/recall`` using the same query.
3. Verify that the returned memory includes the original payload.
"""

import pytest
import uuid


@pytest.mark.asyncio
async def test_basic_recall(client):
    """Store a memory and ensure it can be recalled.

    The payload contains a unique identifier so the test can reliably match the
    returned result even if the underlying memory store already holds other
    entries.
    """
    # Create a unique payload
    unique_id = str(uuid.uuid4())
    payload = {
        "task": f"test-recall-{unique_id}",
        "content": "the quick brown fox jumps over the lazy dog",
        "importance": 0.9,
    }

    # Store the memory
    remember_resp = await client.post("/remember", json=payload)
    assert remember_resp.status_code == 200, "Remember endpoint should succeed"

    # Recall using the same task string as the query
    recall_resp = await client.post("/recall", json={"query": payload["task"]})
    assert recall_resp.status_code == 200, "Recall endpoint should succeed"
    data = recall_resp.json()
    # The response schema includes a ``results`` list; ensure our payload appears.
    results = data.get("results", [])
    assert any(r.get("task") == payload["task"] for r in results), (
        "Recall should return the stored memory"
    )
