"""Graph Client for SomaBrain.

Provides graph operations (links, neighbors, paths) via SFM HTTP API.
Per Requirements B1, B2, B3.
Observability: Prometheus metrics and OpenTelemetry spans per H2.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from opentelemetry import trace

if TYPE_CHECKING:
    from somabrain.memory.transport import MemoryHTTPTransport

from somabrain.memory.graph_metrics import (
    SB_GRAPH_LINK_TOTAL,
    SB_GRAPH_LINK_LATENCY,
    SB_GRAPH_NEIGHBORS_TOTAL,
    SB_GRAPH_NEIGHBORS_LATENCY,
    SB_GRAPH_PATH_TOTAL,
    SB_GRAPH_PATH_LATENCY,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphLink:
    """Represents a graph link between two coordinates."""

    from_coord: Tuple[float, ...]
    to_coord: Tuple[float, ...]
    link_type: str
    strength: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
    tenant: str = "default"
    created_at: float = 0.0


@dataclass
class GraphNeighbor:
    """Represents a neighbor in the graph."""

    coord: Tuple[float, ...]
    link_type: str
    strength: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


class GraphClient:
    """Client for graph operations via SFM HTTP API.

    Per Requirements B1.1-B1.5, B2.1-B2.5, B3.1-B3.5:
    - Creates links between memory coordinates
    - Retrieves neighbors for graph-augmented recall
    - Finds shortest paths between coordinates
    - Queues failed operations to outbox for retry
    """

    def __init__(
        self,
        transport: "MemoryHTTPTransport",  # noqa: F821 - TYPE_CHECKING import
        tenant: str = "default",
        timeout_ms: float = 100.0,
    ):
        """Initialize GraphClient.

        Args:
            transport: HTTP transport for SFM communication.
            tenant: Tenant ID for isolation.
            timeout_ms: Timeout for graph operations (default 100ms per B2.5).
        """
        self._transport = transport
        self._tenant = tenant
        self._timeout_s = timeout_ms / 1000.0

    def _coord_to_str(self, coord: Tuple[float, ...]) -> str:
        """Convert coordinate tuple to comma-separated string."""
        return ",".join(str(c) for c in coord)

    def _str_to_coord(self, coord_str: str) -> Tuple[float, ...]:
        """Convert comma-separated string to coordinate tuple."""
        return tuple(float(c) for c in coord_str.split(","))

    def create_link(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        link_type: str = "related",
        strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a link between two coordinates.

        Per Requirement B1.1: Creates a directed link in the graph store.
        Per Requirement B1.3: Queues to outbox on failure.
        Observability: Prometheus metrics and OpenTelemetry spans per H2.

        Args:
            from_coord: Source coordinate.
            to_coord: Target coordinate.
            link_type: Type of link (e.g., "co_recalled", "promoted_from").
            strength: Link strength (0.0 to 1.0).
            metadata: Optional additional metadata.

        Returns:
            True if link created successfully, False otherwise.
        """
        # OpenTelemetry span for tracing (H1)
        tracer = trace.get_tracer("soma.graph_client")
        with tracer.start_as_current_span("sb_graph_link_create") as span:
            span.set_attribute("tenant", self._tenant)
            span.set_attribute("link_type", link_type)
            span.set_attribute("from_coord", self._coord_to_str(from_coord))
            span.set_attribute("to_coord", self._coord_to_str(to_coord))
            start_time = time.perf_counter()

            if self._transport is None or self._transport.client is None:
                logger.warning("GraphClient: transport not available")
                SB_GRAPH_LINK_TOTAL.labels(
                    tenant=self._tenant, link_type=link_type, status="no_transport"
                ).inc()
                self._queue_to_outbox(
                    "graph.link",
                    {
                        "from_coord": from_coord,
                        "to_coord": to_coord,
                        "link_type": link_type,
                        "strength": strength,
                        "metadata": metadata,
                    },
                )
                return False

            body = {
                "from_coord": self._coord_to_str(from_coord),
                "to_coord": self._coord_to_str(to_coord),
                "link_type": link_type,
                "strength": strength,
            }
            if metadata:
                body["metadata"] = metadata

            headers = {
                "X-Soma-Tenant": self._tenant,
            }

            try:
                response = self._transport.client.post(
                    "/graph/link",
                    json=body,
                    headers=headers,
                    timeout=self._timeout_s,
                )
                duration = time.perf_counter() - start_time
                if response.status_code == 200:
                    SB_GRAPH_LINK_TOTAL.labels(
                        tenant=self._tenant, link_type=link_type, status="success"
                    ).inc()
                    SB_GRAPH_LINK_LATENCY.labels(
                        tenant=self._tenant, link_type=link_type
                    ).observe(duration)
                    return True
                else:
                    SB_GRAPH_LINK_TOTAL.labels(
                        tenant=self._tenant, link_type=link_type, status="http_error"
                    ).inc()
                    SB_GRAPH_LINK_LATENCY.labels(
                        tenant=self._tenant, link_type=link_type
                    ).observe(duration)
                    logger.warning(
                        "Graph link creation failed",
                        status=response.status_code,
                        from_coord=from_coord,
                        to_coord=to_coord,
                    )
                    self._queue_to_outbox(
                        "graph.link",
                        {
                            "from_coord": from_coord,
                            "to_coord": to_coord,
                            "link_type": link_type,
                            "strength": strength,
                            "metadata": metadata,
                        },
                    )
                    return False
            except Exception as exc:
                duration = time.perf_counter() - start_time
                SB_GRAPH_LINK_TOTAL.labels(
                    tenant=self._tenant, link_type=link_type, status="exception"
                ).inc()
                SB_GRAPH_LINK_LATENCY.labels(
                    tenant=self._tenant, link_type=link_type
                ).observe(duration)
                span.record_exception(exc)
                logger.error("Graph link creation exception", error=str(exc))
                self._queue_to_outbox(
                    "graph.link",
                    {
                        "from_coord": from_coord,
                        "to_coord": to_coord,
                        "link_type": link_type,
                        "strength": strength,
                        "metadata": metadata,
                    },
                )
                return False

    def get_neighbors(
        self,
        coord: Tuple[float, ...],
        k_hop: int = 1,
        limit: int = 10,
        link_type: Optional[str] = None,
    ) -> List[GraphNeighbor]:
        """Get neighbors of a coordinate.

        Per Requirement B2.1: Returns k-hop neighbors for graph-augmented recall.
        Per Requirement B2.5: Times out after 100ms.
        Observability: Prometheus metrics and OpenTelemetry spans per H2.

        Args:
            coord: The coordinate to find neighbors for.
            k_hop: Number of hops to traverse (default 1).
            limit: Maximum number of neighbors to return.
            link_type: Optional filter by link type.

        Returns:
            List of GraphNeighbor objects.
        """
        # OpenTelemetry span for tracing (H1)
        tracer = trace.get_tracer("soma.graph_client")
        with tracer.start_as_current_span("sb_graph_neighbors_query") as span:
            span.set_attribute("tenant", self._tenant)
            span.set_attribute("coord", self._coord_to_str(coord))
            span.set_attribute("k_hop", k_hop)
            span.set_attribute("limit", limit)
            if link_type:
                span.set_attribute("link_type", link_type)
            start_time = time.perf_counter()

            if self._transport is None or self._transport.client is None:
                logger.warning("GraphClient: transport not available for get_neighbors")
                SB_GRAPH_NEIGHBORS_TOTAL.labels(
                    tenant=self._tenant, status="no_transport"
                ).inc()
                return []

            params = {
                "coord": self._coord_to_str(coord),
                "k_hop": k_hop,
                "limit": limit,
            }
            if link_type:
                params["link_type"] = link_type

            headers = {
                "X-Soma-Tenant": self._tenant,
            }

            try:
                response = self._transport.client.get(
                    "/graph/neighbors",
                    params=params,
                    headers=headers,
                    timeout=self._timeout_s,
                )
                duration = time.perf_counter() - start_time
                if response.status_code == 200:
                    data = response.json()
                    neighbors = []
                    for n in data.get("neighbors", []):
                        coord_str = n.get("coord", n.get("coordinate", ""))
                        if coord_str:
                            neighbors.append(
                                GraphNeighbor(
                                    coord=self._str_to_coord(coord_str),
                                    link_type=n.get("link_type", "unknown"),
                                    strength=float(n.get("strength", 1.0)),
                                    metadata=n.get("metadata"),
                                )
                            )
                    span.set_attribute("neighbors_count", len(neighbors))
                    SB_GRAPH_NEIGHBORS_TOTAL.labels(
                        tenant=self._tenant, status="success"
                    ).inc()
                    SB_GRAPH_NEIGHBORS_LATENCY.labels(tenant=self._tenant).observe(
                        duration
                    )
                    return neighbors
                else:
                    SB_GRAPH_NEIGHBORS_TOTAL.labels(
                        tenant=self._tenant, status="http_error"
                    ).inc()
                    SB_GRAPH_NEIGHBORS_LATENCY.labels(tenant=self._tenant).observe(
                        duration
                    )
                    logger.warning(
                        "Graph neighbors query failed",
                        status=response.status_code,
                        coord=coord,
                    )
                    return []
            except Exception as exc:
                duration = time.perf_counter() - start_time
                SB_GRAPH_NEIGHBORS_TOTAL.labels(
                    tenant=self._tenant, status="exception"
                ).inc()
                SB_GRAPH_NEIGHBORS_LATENCY.labels(tenant=self._tenant).observe(duration)
                span.record_exception(exc)
                # B2.6: Return empty on timeout (degraded mode)
                logger.warning("Graph neighbors exception (degraded)", error=str(exc))
                return []

    def find_path(
        self,
        from_coord: Tuple[float, ...],
        to_coord: Tuple[float, ...],
        max_length: int = 10,
        link_type: Optional[str] = None,
    ) -> List[Tuple[float, ...]]:
        """Find shortest path between two coordinates.

        Per Requirement B3.1: Returns shortest path as list of coordinates.
        Per Requirement B3.3: Returns empty list if no path exists (not error).
        Per Requirement B3.4: Terminates if path length > max_length.
        Observability: Prometheus metrics and OpenTelemetry spans per H2.

        Args:
            from_coord: Starting coordinate.
            to_coord: Target coordinate.
            max_length: Maximum path length to search.
            link_type: Optional filter by link type.

        Returns:
            List of coordinates in the path, or empty list if no path.
        """
        # OpenTelemetry span for tracing (H1)
        tracer = trace.get_tracer("soma.graph_client")
        with tracer.start_as_current_span("sb_graph_path_query") as span:
            span.set_attribute("tenant", self._tenant)
            span.set_attribute("from_coord", self._coord_to_str(from_coord))
            span.set_attribute("to_coord", self._coord_to_str(to_coord))
            span.set_attribute("max_length", max_length)
            if link_type:
                span.set_attribute("link_type", link_type)
            start_time = time.perf_counter()

            if self._transport is None or self._transport.client is None:
                logger.warning("GraphClient: transport not available for find_path")
                SB_GRAPH_PATH_TOTAL.labels(
                    tenant=self._tenant, status="no_transport", found="false"
                ).inc()
                return []

            params = {
                "from_coord": self._coord_to_str(from_coord),
                "to_coord": self._coord_to_str(to_coord),
                "max_length": max_length,
            }
            if link_type:
                params["link_type"] = link_type

            headers = {
                "X-Soma-Tenant": self._tenant,
            }

            try:
                response = self._transport.client.get(
                    "/graph/path",
                    params=params,
                    headers=headers,
                    timeout=self._timeout_s * 2,  # Allow more time for path search
                )
                duration = time.perf_counter() - start_time
                if response.status_code == 200:
                    data = response.json()
                    if data.get("found"):
                        path = []
                        for coord_str in data.get("path", []):
                            path.append(self._str_to_coord(coord_str))
                        span.set_attribute("path_found", True)
                        span.set_attribute("path_length", len(path))
                        SB_GRAPH_PATH_TOTAL.labels(
                            tenant=self._tenant, status="success", found="true"
                        ).inc()
                        SB_GRAPH_PATH_LATENCY.labels(tenant=self._tenant).observe(
                            duration
                        )
                        return path
                    span.set_attribute("path_found", False)
                    SB_GRAPH_PATH_TOTAL.labels(
                        tenant=self._tenant, status="success", found="false"
                    ).inc()
                    SB_GRAPH_PATH_LATENCY.labels(tenant=self._tenant).observe(duration)
                    return []
                else:
                    SB_GRAPH_PATH_TOTAL.labels(
                        tenant=self._tenant, status="http_error", found="false"
                    ).inc()
                    SB_GRAPH_PATH_LATENCY.labels(tenant=self._tenant).observe(duration)
                    logger.warning(
                        "Graph path query failed",
                        status=response.status_code,
                    )
                    return []
            except Exception as exc:
                duration = time.perf_counter() - start_time
                SB_GRAPH_PATH_TOTAL.labels(
                    tenant=self._tenant, status="exception", found="false"
                ).inc()
                SB_GRAPH_PATH_LATENCY.labels(tenant=self._tenant).observe(duration)
                span.record_exception(exc)
                # B3.3: Return empty on error
                logger.warning("Graph path exception", error=str(exc))
                return []

    def create_co_recalled_links(
        self,
        coords: List[Tuple[float, ...]],
        strength: float = 0.5,
    ) -> int:
        """Create co_recalled links between all pairs of coordinates.

        Per Requirement B1.4: Creates links when multiple memories are recalled together.

        Args:
            coords: List of coordinates that were recalled together.
            strength: Link strength (default 0.5 for co-recall).

        Returns:
            Number of links successfully created.
        """
        if len(coords) < 2:
            return 0

        created = 0
        timestamp = time.time()

        # Create links between all pairs
        for i, from_coord in enumerate(coords):
            for to_coord in coords[i + 1 :]:
                metadata = {
                    "timestamp": timestamp,
                    "tenant_id": self._tenant,
                }
                if self.create_link(
                    from_coord,
                    to_coord,
                    link_type="co_recalled",
                    strength=strength,
                    metadata=metadata,
                ):
                    created += 1

        logger.info(
            "Created co_recalled links",
            total_coords=len(coords),
            links_created=created,
        )
        return created

    def _queue_to_outbox(self, topic: str, payload: Dict[str, Any]) -> None:
        """Queue a failed operation to the outbox for retry.

        Per Requirement B1.3: Failed links are queued for later replay.
        Uses the enhanced outbox with idempotency keys per E2.4.
        """
        try:
            from somabrain.db.outbox import (
                enqueue_memory_event,
                OutboxBackpressureError,
            )

            # Extract coordinates for idempotency key
            from_coord = payload.get("from_coord")
            to_coord = payload.get("to_coord")
            coord = None
            extra_key = None

            if from_coord and to_coord:
                # Use from_coord as primary coordinate
                if isinstance(from_coord, (list, tuple)):
                    coord = tuple(from_coord)
                # Use to_coord as extra key for uniqueness
                if isinstance(to_coord, (list, tuple)):
                    extra_key = ",".join(str(c) for c in to_coord)

            enqueue_memory_event(
                topic=topic,
                payload=payload,
                tenant_id=self._tenant,
                coord=coord,
                extra_key=extra_key,
                check_backpressure_flag=False,  # Don't block on backpressure for retries
            )
            logger.debug(f"Queued {topic} to outbox for retry")
        except OutboxBackpressureError as exc:
            logger.warning(
                "Outbox backpressure, link will not be retried",
                pending_count=exc.pending_count,
            )
        except ImportError:
            logger.warning("Outbox not available, link will not be retried")
        except Exception as exc:
            logger.error("Failed to queue to outbox", error=str(exc))
