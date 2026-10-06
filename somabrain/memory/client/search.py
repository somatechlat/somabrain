from __future__ import annotations

from somabrain.memory.recall_ops import MemoryRecallUnavailable

from .ranking import _deduplicate_hits, _rescore_and_rank_hits
from .serialization import _compat_enrich_payload, _normalize_recall_hits
from .types import RecallHit


class SearchMixin:
    """Handles memory search and recall aggregation."""

    def _memories_search_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
        embedding: list[float] | None = None,
    ) -> list[RecallHit]:
        """Search memories over HTTP. A genuine no-hits response is ``[]``.

        Fail-closed (T-5): every non-success on this path raises
        :class:`MemoryRecallUnavailable` — the same typed failure
        ``recall_ops.memories_search_sync`` raises. Every ``return []`` below is
        a **successful empty**: the store answered and nothing matched.
        """
        if self._http is None:
            raise MemoryRecallUnavailable(
                "recall refused: HTTP memory service is not configured"
            )

        _, compat_universe, compat_headers = _compat_enrich_payload(
            self.cfg, {"query": query, "universe": universe or "real"}, query
        )
        universe_value = str(compat_universe or universe or "real")
        headers = {"X-Request-ID": request_id}
        headers.update(compat_headers)

        # Fetch a larger candidate set from the backend so that post-processing
        # (keyword filtering, re-ranking, deduplication) has enough material to
        # surface semantically or lexically relevant hits even when the backend's
        # raw score ordering is not query-aligned. The multiplier is a compromise
        # between recall coverage and latency for the common top_k=1 case.
        fetch_limit = max(int(top_k) * 5, 50)
        query_text = str(query or "")
        from somabrain.memory.client.transport import build_search_payload

        body = build_search_payload(
            query=query_text,
            top_k=fetch_limit,
            embedding=embedding,
            tenant_id=headers.get("X-Soma-Tenant"),
        )

        success, status, data = self._http_post_with_retries_sync(
            "/memories/search", body, headers
        )
        if success:
            hits = _normalize_recall_hits(data)
            if not hits:
                return []

            if universe_value:
                filtered_hits = [
                    hit
                    for hit in hits
                    if str((hit.payload or {}).get("universe") or universe_value)
                    == universe_value
                ]
                hits = filtered_hits
                if not hits:
                    return []

            deduped = _deduplicate_hits(hits)
            if not deduped:
                return []

            ranked = _rescore_and_rank_hits(
                self.cfg, self._scorer, self._embedder, deduped, query_text
            )
            limit = max(1, int(top_k))
            return ranked[:limit]

        if status in (404, 405, 422):
            raise MemoryRecallUnavailable(
                "Memory search endpoint unavailable or incompatible with current SomaBrain build."
            )

        raise MemoryRecallUnavailable(
            f"Memory search failed with status {status}; recall unavailable."
        )

    async def _memories_search_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
        embedding: list[float] | None = None,
    ) -> list[RecallHit]:
        """Async search. Same contract as :meth:`_memories_search_sync`.

        Every ``return []`` is a successful empty; an outage raises
        :class:`MemoryRecallUnavailable` (T-5).
        """
        if self._http_async is None:
            raise MemoryRecallUnavailable(
                "recall refused: async HTTP memory service is not configured"
            )

        _, compat_universe, compat_headers = _compat_enrich_payload(
            self.cfg, {"query": query, "universe": universe or "real"}, query
        )
        universe_value = str(compat_universe or universe or "real")
        headers = {"X-Request-ID": request_id}
        headers.update(compat_headers)

        # Fetch a larger candidate set from the backend so that post-processing
        # (keyword filtering, re-ranking, deduplication) has enough material to
        # surface semantically or lexically relevant hits even when the backend's
        # raw score ordering is not query-aligned. The multiplier is a compromise
        # between recall coverage and latency for the common top_k=1 case.
        fetch_limit = max(int(top_k) * 5, 50)
        query_text = str(query or "")
        from somabrain.memory.client.transport import build_search_payload

        body = build_search_payload(
            query=query_text,
            top_k=fetch_limit,
            embedding=embedding,
            tenant_id=headers.get("X-Soma-Tenant"),
        )

        success, status, data = await self._http_post_with_retries_async(
            "/memories/search", body, headers
        )
        if success:
            hits = _normalize_recall_hits(data)
            if not hits:
                return []

            if universe_value:
                filtered_hits = [
                    hit
                    for hit in hits
                    if str((hit.payload or {}).get("universe") or universe_value)
                    == universe_value
                ]
                hits = filtered_hits
                if not hits:
                    return []

            deduped = _deduplicate_hits(hits)
            if not deduped:
                return []

            ranked = _rescore_and_rank_hits(
                self.cfg, self._scorer, self._embedder, deduped, query_text
            )
            limit = max(1, int(top_k))
            return ranked[:limit]

        if status in (404, 405, 422):
            raise MemoryRecallUnavailable(
                "Memory search endpoint unavailable or incompatible with current SomaBrain build."
            )

        raise MemoryRecallUnavailable(
            f"Memory search failed with status {status}; recall unavailable."
        )

    def _http_recall_aggregate_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
        embedding: list[float] | None = None,
    ) -> list[RecallHit]:
        return self._memories_search_sync(query, top_k, universe, request_id, embedding=embedding)

    async def _http_recall_aggregate_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
        embedding: list[float] | None = None,
    ) -> list[RecallHit]:
        return await self._memories_search_async(query, top_k, universe, request_id, embedding=embedding)
