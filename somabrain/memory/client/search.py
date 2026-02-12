from __future__ import annotations
from typing import List
from .types import RecallHit
from .serialization import _compat_enrich_payload, _normalize_recall_hits
from .ranking import _filter_hits_by_keyword, _deduplicate_hits, _rescore_and_rank_hits

class SearchMixin:
    """Handles memory search and recall aggregation."""

    def _memories_search_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        if self._http is None:
            raise RuntimeError("HTTP memory service required but not configured")

        _, compat_universe, compat_headers = _compat_enrich_payload(
            self.cfg, {"query": query, "universe": universe or "real"}, query
        )
        universe_value = str(compat_universe or universe or "real")
        headers = {"X-Request-ID": request_id}
        headers.update(compat_headers)

        fetch_limit = max(int(top_k) * 3, 10)
        query_text = str(query or "")
        body = {
            "query": query_text,
            "top_k": fetch_limit,
        }

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

            hits = _filter_hits_by_keyword(hits, query_text)
            if not hits:
                return []

            deduped = _deduplicate_hits(hits)
            if not deduped:
                return []

            ranked = _rescore_and_rank_hits(self.cfg, self._scorer, self._embedder, deduped, query_text)
            limit = max(1, int(top_k))
            return ranked[:limit]

        if status in (404, 405, 422):
            raise RuntimeError(
                "Memory search endpoint unavailable or incompatible with current SomaBrain build."
            )

        return []

    async def _memories_search_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        if self._http_async is None:
            raise RuntimeError("Async HTTP memory service required but not configured")

        _, compat_universe, compat_headers = _compat_enrich_payload(
            self.cfg, {"query": query, "universe": universe or "real"}, query
        )
        universe_value = str(compat_universe or universe or "real")
        headers = {"X-Request-ID": request_id}
        headers.update(compat_headers)

        fetch_limit = max(int(top_k) * 3, 10)
        query_text = str(query or "")
        body = {
            "query": query_text,
            "top_k": fetch_limit,
        }

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

            hits = _filter_hits_by_keyword(hits, query_text)
            if not hits:
                return []

            deduped = _deduplicate_hits(hits)
            if not deduped:
                return []

            ranked = _rescore_and_rank_hits(self.cfg, self._scorer, self._embedder, deduped, query_text)
            limit = max(1, int(top_k))
            return ranked[:limit]

        if status in (404, 405, 422):
            raise RuntimeError(
                "Memory search endpoint unavailable or incompatible with current build."
            )

        return []

    def _http_recall_aggregate_sync(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        return self._memories_search_sync(query, top_k, universe, request_id)

    async def _http_recall_aggregate_async(
        self,
        query: str,
        top_k: int,
        universe: str,
        request_id: str,
    ) -> List[RecallHit]:
        return await self._memories_search_async(query, top_k, universe, request_id)
