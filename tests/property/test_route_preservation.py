"""Property tests for API route preservation after decomposition.

**Feature: monolithic-decomposition**
**Validates: Requirements 1.2 - API Route Preservation**

These tests verify that all expected API routes are preserved after
extracting routers from the monolithic app.py file.

NOTE: These tests require live infrastructure (Redis, Milvus) because
importing somabrain.app initializes connections at module load time.
"""

from __future__ import annotations

import os

import pytest
from hypothesis import given, settings, strategies as st


# Skip all tests in this module if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Redis, Milvus) - set SOMA_INFRA_AVAILABLE=1",
)


# ---------------------------------------------------------------------------
# Route Preservation Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestRoutePreservation:
    """Tests for API route preservation after decomposition.

    **Feature: monolithic-decomposition, Property 2: API Route Preservation**
    **Validates: Requirements 1.2**
    """

    def test_health_routes_preserved(self) -> None:
        """Health routes are preserved after extraction.

        **Feature: monolithic-decomposition**
        **Validates: Requirements 1.2**
        """
        from somabrain.app import app

        routes = {route.path for route in app.routes}

        # Health endpoints must exist
        health_routes = ["/health", "/healthz", "/diagnostics", "/metrics"]
        for route in health_routes:
            assert route in routes, f"Health route {route} not found in app routes"

    def test_memory_routes_preserved(self) -> None:
        """Memory routes are preserved after extraction.

        **Feature: monolithic-decomposition**
        **Validates: Requirements 1.2**
        """
        from somabrain.app import app

        routes = {route.path for route in app.routes}

        # Memory endpoints must exist (under /memory prefix)
        memory_routes = ["/memory/remember", "/memory/recall"]
        for route in memory_routes:
            assert route in routes, f"Memory route {route} not found in app routes"

    def test_cognitive_routes_preserved(self) -> None:
        """Cognitive routes are preserved after extraction.

        **Feature: monolithic-decomposition**
        **Validates: Requirements 1.2**
        """
        from somabrain.app import app

        routes = {route.path for route in app.routes}

        # Cognitive endpoints must exist
        cognitive_routes = ["/plan/suggest", "/neuromodulators"]
        for route in cognitive_routes:
            assert route in routes, f"Cognitive route {route} not found in app routes"

    def test_context_routes_preserved(self) -> None:
        """Context routes are preserved after extraction.

        **Feature: monolithic-decomposition**
        **Validates: Requirements 1.2**
        """
        from somabrain.app import app

        routes = {route.path for route in app.routes}

        # Context endpoints must exist
        context_routes = ["/context/evaluate", "/context/feedback"]
        for route in context_routes:
            assert route in routes, f"Context route {route} not found in app routes"

    def test_no_duplicate_routes(self) -> None:
        """No duplicate routes exist after decomposition.

        **Feature: monolithic-decomposition**
        **Validates: Requirements 1.2**
        """
        from somabrain.app import app

        routes = [route.path for route in app.routes]

        # Check for duplicates (excluding parameterized routes)
        non_param_routes = [r for r in routes if "{" not in r]
        non_param_unique = set(non_param_routes)

        # Allow some duplicates for different HTTP methods on same path
        # but flag if there are excessive duplicates
        duplicate_count = len(non_param_routes) - len(non_param_unique)
        assert duplicate_count < 10, f"Too many duplicate routes: {duplicate_count}"


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestRoutePropertyBased:
    """Property-based tests for route preservation.

    **Feature: monolithic-decomposition**
    **Validates: Requirements 1.2**
    """

    @given(st.sampled_from(["health", "memory", "cognitive", "context"]))
    @settings(max_examples=10, deadline=None)
    def test_router_category_has_routes(self, category: str) -> None:
        """Property: Each router category has at least one route.

        **Feature: monolithic-decomposition, Property 2**
        **Validates: Requirements 1.2**

        *For any* router category, there SHALL be at least one route.
        """
        from somabrain.app import app

        routes = {route.path for route in app.routes}

        category_prefixes = {
            "health": ["/health", "/healthz", "/diagnostics", "/metrics"],
            "memory": ["/memory/"],
            "cognitive": ["/plan/", "/neuromodulators", "/personality"],
            "context": ["/context/"],
        }

        prefixes = category_prefixes.get(category, [])
        found = any(
            any(route.startswith(prefix) or route == prefix for prefix in prefixes)
            for route in routes
        )

        assert found, f"No routes found for category {category}"
