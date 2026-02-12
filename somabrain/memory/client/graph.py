from __future__ import annotations
import uuid
import asyncio
import logging
from typing import List, Tuple
from .serialization import _response_json

logger = logging.getLogger(__name__)

class GraphMixin:
    """Handles graph operations (linking, unlinking, traversal)."""

    def link(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE UNAVAILABLE: link requires an HTTP memory backend."
            )
        try:
            rid = request_id or str(uuid.uuid4())
            rid_hdr = {"X-Request-ID": rid}
            self._http.post(
                "/link",
                json={
                    "from_coord": f"{from_coord[0]},{from_coord[1]},{from_coord[2]}",
                    "to_coord": f"{to_coord[0]},{to_coord[1]},{to_coord[2]}",
                    "type": link_type,
                    "weight": weight,
                },
                headers=rid_hdr,
            )
        except Exception as exc:
            logger.debug("link request failed: %r", exc)

    async def alink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str = "related",
        weight: float = 1.0,
        request_id: str | None = None,
    ) -> None:
        if self._http_async is not None:
            rid = request_id or str(uuid.uuid4())
            headers = {"X-Request-ID": rid}
            try:
                await self._http_async.post(
                    "/link",
                    json={
                        "from_coord": f"{from_coord[0]},{from_coord[1]},{from_coord[2]}",
                        "to_coord": f"{to_coord[0]},{to_coord[1]},{to_coord[2]}",
                        "type": link_type,
                        "weight": weight,
                    },
                    headers=headers,
                )
                return
            except Exception as exc:
                logger.debug("async link request failed: %r", exc)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self.link(
                from_coord,
                to_coord,
                link_type=link_type,
                weight=weight,
                request_id=request_id,
            ),
        )

    def links_from(
        self,
        start: Tuple[float, float, float],
        type_filter: str | None = None,
        limit: int = 50,
    ) -> List[dict]:
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE UNAVAILABLE: links_from requires an HTTP memory backend."
            )

        unlimited = int(limit) <= 0
        max_items = None if unlimited else int(limit)
        out: List[dict] = []
        try:
            body = {
                "from_coord": [float(start[0]), float(start[1]), float(start[2])],
                "type": str(type_filter) if type_filter else None,
                "limit": int(limit),
            }
            resp = self._http.post("/neighbors", json=body)
            data = _response_json(resp)
            if isinstance(data, dict):
                edges = data.get("edges") or data.get("results") or []
            else:
                edges = []
            for edge in edges:
                try:
                    raw_from = edge.get("from") or start
                    raw_to = edge.get("to") or start
                    if isinstance(raw_from, (list, tuple)) and len(raw_from) >= 3:
                        from_vec = (float(raw_from[0]), float(raw_from[1]), float(raw_from[2]))
                    else:
                        from_vec = (float(start[0]), float(start[1]), float(start[2]))
                    if isinstance(raw_to, (list, tuple)) and len(raw_to) >= 3:
                        to_vec = (float(raw_to[0]), float(raw_to[1]), float(raw_to[2]))
                    else:
                        to_vec = (float(start[0]), float(start[1]), float(start[2]))
                    if type_filter and edge.get("type") != type_filter:
                        continue
                    out.append(
                        {
                            "from": from_vec,
                            "to": to_vec,
                            "type": edge.get("type"),
                            "weight": float(edge.get("weight", 1.0)),
                        }
                    )
                    if not unlimited and max_items is not None and len(out) >= max_items:
                        break
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("links_from request failed: %r", exc)
            return []

        return out if unlimited else out[:max_items]

    def unlink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE UNAVAILABLE: unlink requires an HTTP memory backend."
            )

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        body = {
            "from_coord": [float(from_coord[0]), float(from_coord[1]), float(from_coord[2])],
            "to_coord": [float(to_coord[0]), float(to_coord[1]), float(to_coord[2])],
            "type": link_type,
        }

        success, _, _ = self._http_post_with_retries_sync("/unlink", body, headers)
        if not success:
            raise RuntimeError("Memory service unavailable (unlink failed)")
        return True

    async def aunlink(
        self,
        from_coord: tuple[float, float, float],
        to_coord: tuple[float, float, float],
        link_type: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        if self._http_async is not None:
            rid = request_id or str(uuid.uuid4())
            headers = {"X-Request-ID": rid}
            body = {
                "from_coord": [float(from_coord[0]), float(from_coord[1]), float(from_coord[2])],
                "to_coord": [float(to_coord[0]), float(to_coord[1]), float(to_coord[2])],
                "type": link_type,
            }
            success, _, _ = await self._http_post_with_retries_async(
                "/unlink", body, headers
            )
            if success:
                return True

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.unlink(
                from_coord,
                to_coord,
                link_type=link_type,
                request_id=request_id,
            ),
        )

    def prune_links(
        self,
        coord: tuple[float, float, float],
        *,
        weight_below: float | None = None,
        max_degree: int | None = None,
        type_filter: str | None = None,
        request_id: str | None = None,
    ) -> int:
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE UNAVAILABLE: prune_links requires an HTTP memory backend."
            )

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        body = {
            "from_coord": [float(coord[0]), float(coord[1]), float(coord[2])],
            "weight_below": weight_below,
            "max_degree": max_degree,
            "type": type_filter,
        }
        success, _, data = self._http_post_with_retries_sync("/prune", body, headers)
        if success and isinstance(data, dict):
            try:
                removed = int(data.get("removed") or data.get("count") or 0)
            except Exception:
                removed = 0
            return removed

        raise RuntimeError("Memory service unavailable (prune_links failed)")

    def degree(self, node: Tuple[float, float, float]) -> int:
        try:
            neighbors = self.links_from(node, limit=1024)
            return len(neighbors)
        except Exception:
            return 0

    def centrality(self, node: Tuple[float, float, float]) -> float:
        try:
            neighbors = self.links_from(node, limit=1024)
            if not neighbors:
                return 0.0
            deg = float(len(neighbors))
            unique_nodes: set[Tuple[float, float, float]] = {
                (float(node[0]), float(node[1]), float(node[2]))
            }
            for edge in neighbors:
                to_coord = edge.get("to")
                if isinstance(to_coord, (list, tuple)) and len(to_coord) >= 3:
                    unique_nodes.add((float(to_coord[0]), float(to_coord[1]), float(to_coord[2])))
            total = len(unique_nodes)
            if total <= 1:
                return 0.0
            return deg / float(total - 1)
        except Exception:
            return 0.0

    def k_hop(
        self,
        starts: List[Tuple[float, float, float]],
        depth: int = 1,
        limit: int = 50,
        type_filter: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        try:
            if not starts:
                return []
            seen: set[Tuple[float, float, float]] = set()
            frontier = [(float(s[0]), float(s[1]), float(s[2])) for s in starts]
            out: list[Tuple[float, float, float]] = []
            for d in range(max(1, int(depth))):
                new_frontier: list[Tuple[float, float, float]] = []
                for node in frontier:
                    if node in seen:
                        continue
                    seen.add(node)
                    try:
                        neigh = self.links_from(node, type_filter=type_filter, limit=limit)
                    except Exception:
                        neigh = []
                    for e in neigh:
                        to_coord = e.get("to")
                        if isinstance(to_coord, (list, tuple)) and len(to_coord) >= 3:
                            t = (float(to_coord[0]), float(to_coord[1]), float(to_coord[2]))
                            if t not in seen and t not in out:
                                out.append(t)
                                new_frontier.append(t)
                                if len(out) >= max(1, int(limit)):
                                    return out
                frontier = new_frontier
                if not frontier:
                    break
            return out
        except Exception:
            return []
