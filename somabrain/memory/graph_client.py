"""Graph Client for SomaBrain.

Provides graph operations (links, neighbors, paths) via SFM HTTP API.
Per Requirements B1, B2, B3.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


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
        transport: "MemoryHTTPTransport",
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

        Args:
            from_coord: Source coordinate.
            to_coord: Target coordinate.
            link_type: Type of link (e.g., "co_recalled", "promoted_from").
            strength: Link strength (0.0 to 1.0).
            metadata: Optional additional metadata.

        Returns:
            True if link created successfully, False otherwise.
        """
        if self._transport is None or self._transport.client is None:
            logger.warning("GraphClient: transport not available")
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
            if response.status_code == 200:
                return True
            else:
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

        Args:
            coord: The coordinate to find neighbors for.
            k_hop: Number of hops to traverse (default 1).
            limit: Maximum number of neighbors to return.
            link_type: Optional filter by link type.

        Returns:
            List of GraphNeighbor objects.
        """
        if self._transport is None or self._transport.client is None:
            logger.warning("GraphClient: transport not available for get_neighbors")
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
                return neighbors
            else:
                logger.warning(
                    "Graph neighbors query failed",
                    status=response.status_code,
                    coord=coord,
                )
                return []
        except Exception as exc:
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

        Args:
            from_coord: Starting coordinate.
            to_coord: Target coordinate.
            max_length: Maximum path length to search.
            link_type: Optional filter by link type.

        Returns:
            List of coordinates in the path, or empty list if no path.
        """
        if self._transport is None or self._transport.client is None:
            logger.warning("GraphClient: transport not available for find_path")
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
            if response.status_code == 200:
                data = response.json()
                if data.get("found"):
                    path = []
                    for coord_str in data.get("path", []):
                        path.append(self._str_to_coord(coord_str))
                    return path
                return []
            else:
                logger.warning(
                    "Graph path query failed",
                    status=response.status_code,
                )
                return []
        except Exception as exc:
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
        """
        try:
            from somabrain.db.outbox import queue_to_outbox

            queue_to_outbox(
                topic=topic,
                payload=payload,
                tenant=self._tenant,
            )
        except ImportError:
            logger.warning("Outbox not available, link will not be retried")
        except Exception as exc:
            logger.error("Failed to queue to outbox", error=str(exc))
