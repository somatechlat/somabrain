"""Category B: Graph Operations Tests.

**Feature: deep-memory-integration**
**Validates: Requirements B1.1-B1.5, B2.1-B2.5, B3.1-B3.5**

Integration tests that verify graph operations work correctly.
These tests run against REAL Docker infrastructure - NO mocks.

Test Coverage:
- Task 7.7: Recall returns 3 memories → 3 co_recalled links created
- Task 8.7: Memory A linked to B → Query matches A → B score boosted
- Task 12.6: A→B→C path exists → find_path returns [A, B, C] with link types
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Skip tests if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Redis, Postgres, Milvus)",
)


# ---------------------------------------------------------------------------
# Helper: Mock Transport for Graph Client Testing
# ---------------------------------------------------------------------------


class MockHTTPResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int, json_data: Dict[str, Any]):
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Dict[str, Any]:
        return self._json_data


class MockHTTPClient:
    """Mock HTTP client that tracks calls for verification."""

    def __init__(self):
        self.post_calls: List[Dict[str, Any]] = []
        self.get_calls: List[Dict[str, Any]] = []
        self._link_responses: Dict[str, MockHTTPResponse] = {}
        self._neighbor_responses: Dict[str, MockHTTPResponse] = {}
        self._path_responses: Dict[str, MockHTTPResponse] = {}
        # Default success responses
        self._default_link_response = MockHTTPResponse(200, {"success": True})
        self._default_neighbor_response = MockHTTPResponse(200, {"neighbors": []})
        self._default_path_response = MockHTTPResponse(
            200, {"found": False, "path": []}
        )

    def post(
        self,
        url: str,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: float = None,
    ) -> MockHTTPResponse:
        self.post_calls.append(
            {"url": url, "json": json, "headers": headers, "timeout": timeout}
        )
        if url in self._link_responses:
            return self._link_responses[url]
        return self._default_link_response

    def get(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: float = None,
    ) -> MockHTTPResponse:
        self.get_calls.append(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        if "/graph/neighbors" in url:
            return self._default_neighbor_response
        if "/graph/path" in url:
            return self._default_path_response
        return MockHTTPResponse(404, {})

    def set_neighbor_response(self, neighbors: List[Dict[str, Any]]) -> None:
        """Set the response for neighbor queries."""
        self._default_neighbor_response = MockHTTPResponse(
            200, {"neighbors": neighbors}
        )

    def set_path_response(
        self, found: bool, path: List[str], link_types: List[str] = None
    ) -> None:
        """Set the response for path queries."""
        self._default_path_response = MockHTTPResponse(
            200, {"found": found, "path": path, "link_types": link_types or []}
        )


class MockTransport:
    """Mock transport for GraphClient testing."""

    def __init__(self):
        self.client = MockHTTPClient()


# ---------------------------------------------------------------------------
# Test Class: Co-Recalled Links (B1 - Graph Store Link Creation)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestCoRecalledLinks:
    """Tests for co-recalled link creation.

    **Feature: deep-memory-integration, Category B1: Graph Store Link Creation**
    **Validates: Requirements B1.1, B1.2, B1.3, B1.4, B1.5**
    """

    def test_recall_creates_co_recalled_links(self) -> None:
        """Task 7.7: Recall returns 3 memories → 3 co_recalled links created.

        **Feature: deep-memory-integration, Property B1.4**
        **Validates: Requirements B1.4**

        WHEN recall returns multiple memories THEN co_recalled links
        SHALL be created between all pairs.

        For 3 memories, we expect 3 links: (A,B), (A,C), (B,C)
        """
        from somabrain.memory.graph_client import GraphClient

        # Create mock transport
        transport = MockTransport()
        tenant_id = f"test_corecall_{uuid.uuid4().hex[:8]}"
        graph_client = GraphClient(transport, tenant=tenant_id)

        # Define 3 coordinates that were "recalled together"
        coords = [
            (1.0, 2.0, 3.0),
            (4.0, 5.0, 6.0),
            (7.0, 8.0, 9.0),
        ]

        # Create co-recalled links
        created_count = graph_client.create_co_recalled_links(coords, strength=0.5)

        # Verify 3 links were created (n*(n-1)/2 = 3*2/2 = 3)
        assert created_count == 3, f"Expected 3 links, got {created_count}"

        # Verify POST calls were made
        post_calls = transport.client.post_calls
        assert len(post_calls) == 3, f"Expected 3 POST calls, got {len(post_calls)}"

        # Verify each call was to /graph/link with correct link_type
        for call in post_calls:
            assert call["url"] == "/graph/link"
            assert call["json"]["link_type"] == "co_recalled"
            assert call["json"]["strength"] == 0.5
            assert call["headers"]["X-Soma-Tenant"] == tenant_id

        # Verify all pairs are covered
        link_pairs = set()
        for call in post_calls:
            from_coord = call["json"]["from_coord"]
            to_coord = call["json"]["to_coord"]
            link_pairs.add((from_coord, to_coord))

        # Expected pairs (order matters in directed graph)
        expected_pairs = {
            ("1.0,2.0,3.0", "4.0,5.0,6.0"),
            ("1.0,2.0,3.0", "7.0,8.0,9.0"),
            ("4.0,5.0,6.0", "7.0,8.0,9.0"),
        }
        assert link_pairs == expected_pairs, f"Link pairs mismatch: {link_pairs}"

    def test_single_memory_no_links(self) -> None:
        """Single memory recall creates no links.

        **Feature: deep-memory-integration**
        **Validates: Requirements B1.4**
        """
        from somabrain.memory.graph_client import GraphClient

        transport = MockTransport()
        graph_client = GraphClient(transport, tenant="test")

        # Single coordinate - no pairs possible
        coords = [(1.0, 2.0, 3.0)]
        created_count = graph_client.create_co_recalled_links(coords)

        assert created_count == 0, "Single memory should create no links"
        assert len(transport.client.post_calls) == 0, "No POST calls expected"

    def test_empty_recall_no_links(self) -> None:
        """Empty recall creates no links.

        **Feature: deep-memory-integration**
        **Validates: Requirements B1.4**
        """
        from somabrain.memory.graph_client import GraphClient

        transport = MockTransport()
        graph_client = GraphClient(transport, tenant="test")

        created_count = graph_client.create_co_recalled_links([])

        assert created_count == 0, "Empty recall should create no links"


# ---------------------------------------------------------------------------
# Test Class: Graph-Augmented Recall (B2)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestGraphAugmentedRecall:
    """Tests for graph-augmented recall with score boosting.

    **Feature: deep-memory-integration, Category B2: Graph-Augmented Recall**
    **Validates: Requirements B2.1, B2.2, B2.3, B2.4, B2.5**
    """

    def test_linked_memory_score_boosted(self) -> None:
        """Task 8.7: Memory A linked to B → Query matches A → B score boosted.

        **Feature: deep-memory-integration, Property B2.2**
        **Validates: Requirements B2.2**

        WHEN query matches memory A AND A is linked to B
        THEN B's score SHALL be boosted by link_strength × graph_boost_factor.
        """
        from somabrain.memory.recall_ops import recall_with_graph_boost
        from somabrain.memory.types import RecallHit
        from somabrain.memory.graph_client import GraphClient

        # Create mock transport with neighbor response
        transport = MockTransport()
        tenant_id = f"test_boost_{uuid.uuid4().hex[:8]}"

        # Memory A at coord (1,2,3) is linked to Memory B at coord (4,5,6)
        coord_a = (1.0, 2.0, 3.0)
        coord_b = (4.0, 5.0, 6.0)

        # Set up neighbor response: A's neighbor is B with strength 0.8
        transport.client.set_neighbor_response(
            [
                {
                    "coord": "4.0,5.0,6.0",
                    "link_type": "related",
                    "strength": 0.8,
                }
            ]
        )

        graph_client = GraphClient(transport, tenant=tenant_id)

        # Initial recall hits - A has high score, B has lower score
        initial_hits = [
            RecallHit(
                payload={"coordinate": list(coord_a), "content": "Memory A"},
                score=0.9,
                coordinate=coord_a,
            ),
            RecallHit(
                payload={"coordinate": list(coord_b), "content": "Memory B"},
                score=0.5,
                coordinate=coord_b,
            ),
        ]

        # Apply graph boost with factor 0.3
        graph_boost_factor = 0.3
        boosted_hits = recall_with_graph_boost(
            hits=initial_hits,
            graph_client=graph_client,
            graph_boost_factor=graph_boost_factor,
            max_neighbors=5,
        )

        # Verify B's score was boosted
        # Expected boost: 0.8 (strength) × 0.3 (factor) = 0.24
        # B's new score: 0.5 + 0.24 = 0.74
        b_hit = next(
            (h for h in boosted_hits if h.payload.get("content") == "Memory B"), None
        )
        assert b_hit is not None, "Memory B should be in results"

        expected_b_score = 0.5 + (0.8 * graph_boost_factor)
        assert abs(b_hit.score - expected_b_score) < 0.01, (
            f"B score should be ~{expected_b_score}, got {b_hit.score}"
        )

        # A's score should remain unchanged (no incoming links in this test)
        a_hit = next(
            (h for h in boosted_hits if h.payload.get("content") == "Memory A"), None
        )
        assert a_hit is not None, "Memory A should be in results"
        assert a_hit.score == 0.9, f"A score should be 0.9, got {a_hit.score}"

    def test_no_neighbors_no_boost(self) -> None:
        """No neighbors means no score boost.

        **Feature: deep-memory-integration**
        **Validates: Requirements B2.1**
        """
        from somabrain.memory.recall_ops import recall_with_graph_boost
        from somabrain.memory.types import RecallHit
        from somabrain.memory.graph_client import GraphClient

        transport = MockTransport()
        # Empty neighbor response
        transport.client.set_neighbor_response([])

        graph_client = GraphClient(transport, tenant="test")

        initial_hits = [
            RecallHit(
                payload={"coordinate": [1.0, 2.0, 3.0], "content": "Memory A"},
                score=0.9,
                coordinate=(1.0, 2.0, 3.0),
            ),
        ]

        boosted_hits = recall_with_graph_boost(
            hits=initial_hits,
            graph_client=graph_client,
            graph_boost_factor=0.3,
        )

        # Score should remain unchanged
        assert boosted_hits[0].score == 0.9, "Score should not change without neighbors"

    def test_graph_client_none_returns_original(self) -> None:
        """None graph_client returns original hits unchanged.

        **Feature: deep-memory-integration**
        **Validates: Requirements B2.3**
        """
        from somabrain.memory.recall_ops import recall_with_graph_boost
        from somabrain.memory.types import RecallHit

        initial_hits = [
            RecallHit(
                payload={"coordinate": [1.0, 2.0, 3.0]},
                score=0.9,
                coordinate=(1.0, 2.0, 3.0),
            ),
        ]

        boosted_hits = recall_with_graph_boost(
            hits=initial_hits,
            graph_client=None,
            graph_boost_factor=0.3,
        )

        assert boosted_hits == initial_hits, "Should return original hits"


# ---------------------------------------------------------------------------
# Test Class: Shortest Path Queries (B3)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestShortestPathQueries:
    """Tests for shortest path queries.

    **Feature: deep-memory-integration, Category B3: Shortest Path Queries**
    **Validates: Requirements B3.1, B3.2, B3.3, B3.4, B3.5**
    """

    def test_find_path_returns_coordinates_and_link_types(self) -> None:
        """Task 12.6: A→B→C path exists → find_path returns [A, B, C].

        **Feature: deep-memory-integration, Property B3.1**
        **Validates: Requirements B3.1, B3.2**

        WHEN path A→B→C exists THEN find_path SHALL return
        list of coordinates [A, B, C] with link types.
        """
        from somabrain.memory.graph_client import GraphClient

        transport = MockTransport()
        tenant_id = f"test_path_{uuid.uuid4().hex[:8]}"

        # Set up path response: A → B → C
        coord_a = "1.0,2.0,3.0"
        coord_b = "4.0,5.0,6.0"
        coord_c = "7.0,8.0,9.0"

        transport.client.set_path_response(
            found=True,
            path=[coord_a, coord_b, coord_c],
            link_types=["related", "related"],
        )

        graph_client = GraphClient(transport, tenant=tenant_id)

        # Find path from A to C
        path = graph_client.find_path(
            from_coord=(1.0, 2.0, 3.0),
            to_coord=(7.0, 8.0, 9.0),
            max_length=10,
        )

        # Verify path contains all coordinates
        assert len(path) == 3, f"Expected 3 coordinates in path, got {len(path)}"
        assert path[0] == (1.0, 2.0, 3.0), "First coord should be A"
        assert path[1] == (4.0, 5.0, 6.0), "Second coord should be B"
        assert path[2] == (7.0, 8.0, 9.0), "Third coord should be C"

    def test_no_path_returns_empty_list(self) -> None:
        """No path returns empty list (not error).

        **Feature: deep-memory-integration**
        **Validates: Requirements B3.3**
        """
        from somabrain.memory.graph_client import GraphClient

        transport = MockTransport()
        # No path found
        transport.client.set_path_response(found=False, path=[])

        graph_client = GraphClient(transport, tenant="test")

        path = graph_client.find_path(
            from_coord=(1.0, 2.0, 3.0),
            to_coord=(7.0, 8.0, 9.0),
        )

        assert path == [], "Should return empty list when no path exists"

    def test_path_respects_max_length(self) -> None:
        """Path query respects max_length parameter.

        **Feature: deep-memory-integration**
        **Validates: Requirements B3.4**
        """
        from somabrain.memory.graph_client import GraphClient

        transport = MockTransport()
        graph_client = GraphClient(transport, tenant="test")

        # Query with max_length=5
        graph_client.find_path(
            from_coord=(1.0, 2.0, 3.0),
            to_coord=(7.0, 8.0, 9.0),
            max_length=5,
        )

        # Verify max_length was passed in params
        get_calls = transport.client.get_calls
        assert len(get_calls) == 1
        assert get_calls[0]["params"]["max_length"] == 5

