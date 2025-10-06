import sys


def main():
    # Ensure imports resolve when running directly
    sys.path.insert(0, ".")

    from somabrain.config import Config
    from somabrain.memory_client import MemoryClient

    cfg = Config()
    cfg.namespace = "test_ns"
    # Memory mode removed; ensure HTTP endpoint is configured for tests
    cfg.http.endpoint = cfg.http.endpoint or "http://localhost:9595"

    mc = MemoryClient(cfg)

    # store_from_payload should succeed even without coordinates (fallback to remember)
    ok = mc.store_from_payload({"task": "foo", "memory_type": "episodic"})
    assert ok is True

    # With coordinates present it should also succeed (local path guarded)
    ok2 = mc.store_from_payload(
        {"coordinate": (0.1, 0.2, 0.3), "task": "bar", "memory_type": "episodic"}
    )
    # In stub mode, coordinate path falls back or no-ops; expect bool result
    assert isinstance(ok2, bool)

    # Simulate an SFM recall response with matches+scores

    class _FakeResponse:
        def __init__(self, data):
            self.status_code = 200
            self._data = data

        def json(self):
            return self._data

    class _RecordingHTTP:
        def __init__(self, recall_data, recall_scores, hybrid_data=None, keyword_data=None):
            self._recall = recall_data
            self._recall_scores = recall_scores
            self._hybrid = hybrid_data or {"results": []}
            self._keyword = keyword_data or {"results": []}
            self.calls = []

        def post(self, endpoint, json=None, headers=None):
            self.calls.append((endpoint, json, headers))
            if endpoint == "/recall":
                return _FakeResponse(self._recall)
            if endpoint == "/recall_with_scores":
                return _FakeResponse(self._recall_scores)
            if endpoint == "/hybrid_recall_with_scores":
                if isinstance(json, dict) and (json.get("query") or "").strip().lower() == "zebra":
                    return _FakeResponse(self._hybrid)
                return _FakeResponse({"results": []})
            if endpoint == "/keyword_search":
                if isinstance(json, dict) and (json.get("term") or "").strip().lower() == "zebra":
                    return _FakeResponse(self._keyword)
                return _FakeResponse({"results": []})
            if endpoint == "/store_bulk":
                items = json.get("items", []) if isinstance(json, dict) else []
                response_items = []
                for item in items:
                    response_items.append(
                        {
                            "coord": item.get("coord"),
                            "payload": item.get("payload"),
                            "score": 0.9,
                        }
                    )
                return _FakeResponse({"items": response_items})
            if endpoint in {"/link", "/unlink"}:
                return _FakeResponse({"ok": True})
            if endpoint == "/prune":
                return _FakeResponse({"removed": 1})
            return _FakeResponse({})

    fake_match = {
        "matches": [
            {
                "payload": {"task": "foo", "phase": "context"},
                "score": 0.42,
                "coord": "0.1,0.2,0.3",
            }
        ]
    }
    fake_match_scores = {
        "matches": [
            {
                "payload": {"task": "bulk win", "text": "bulk memory win"},
                "score": 0.88,
                "coordinate": [0.4, 0.5, 0.6],
            }
        ]
    }
    fake_hybrid = {
        "results": [
            {
                "payload": {
                    "text": "Hybrid zebra memory",
                    "content": "Hybrid zebra memory",
                    "memory_type": "episodic",
                    "coordinate": [0.9, 0.1, 0.2],
                },
                "score": 0.65,
            }
        ]
    }
    fake_keyword = {
        "results": [
            {
                "text": "Keyword zebra spotlight",
                "content": "Keyword zebra spotlight",
                "memory_type": "episodic",
                "coordinate": [0.25, 0.35, 0.45],
            }
        ]
    }
    mc._http = _RecordingHTTP(fake_match, fake_match_scores, fake_hybrid, fake_keyword)
    hits = mc.recall("foo", top_k=1)
    assert len(hits) == 1
    assert hits[0].score is not None
    assert abs(hits[0].score - 0.88) < 1e-9
    assert hits[0].payload.get("_source_endpoint") == "/recall_with_scores"
    assert hits[0].payload.get("_score") == hits[0].score
    assert hits[0].coordinate and len(hits[0].coordinate) == 3

    # remember_bulk should return coordinates and surface them in recall_with_scores
    bulk_coords = mc.remember_bulk([
        ("bulk-key", {"task": "bulk memory win", "memory_type": "episodic"})
    ])
    assert len(bulk_coords) == 1
    bulk_hits = mc.recall_with_scores("bulk", top_k=1)
    assert bulk_hits and bulk_hits[0].score is not None

    # Graph helpers: link -> unlink -> prune
    from_coord = bulk_coords[0]
    to_coord = mc.coord_for_key("neighbor")
    mc.link(from_coord, to_coord, weight=0.05)
    mc.link(from_coord, mc.coord_for_key("neighbor2"), weight=0.1)
    assert mc.links_from(from_coord)
    assert mc.unlink(from_coord, to_coord) is True
    remaining = mc.links_from(from_coord)
    assert all(tuple(edge["to"]) != tuple(to_coord) for edge in remaining)
    removed_count = mc.prune_links(from_coord, weight_below=0.09)
    assert removed_count >= 1

    # Aggregated recall should surface keyword/hybrid matches when vector hits miss
    zebra_hits = mc.recall("zebra", top_k=3)
    assert zebra_hits, "Expected aggregated recall to return zebra memories"
    sources = [hit.payload.get("_source_endpoint") for hit in zebra_hits]
    assert "/keyword_search" in sources, "Keyword search results should be merged"
    keyword_hit = next(
        (hit for hit in zebra_hits if hit.payload.get("_source_endpoint") == "/keyword_search"),
        None,
    )
    assert keyword_hit is not None
    assert keyword_hit.score is not None and keyword_hit.score > 0
    assert "zebra" in (keyword_hit.payload.get("text") or keyword_hit.payload.get("content") or "").lower()

    print("MemoryClient tests passed.")


if __name__ == "__main__":
    main()
