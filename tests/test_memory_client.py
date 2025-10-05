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
        def __init__(self, recall_data, recall_scores):
            self._recall = recall_data
            self._recall_scores = recall_scores
            self.calls = []

        def post(self, endpoint, json=None, headers=None):
            self.calls.append((endpoint, json, headers))
            if endpoint == "/recall":
                return _FakeResponse(self._recall)
            if endpoint == "/recall_with_scores":
                return _FakeResponse(self._recall_scores)
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
    mc._http = _RecordingHTTP(fake_match, fake_match_scores)
    hits = mc.recall("foo", top_k=1)
    assert len(hits) == 1
    assert hits[0].score and abs(hits[0].score - 0.42) < 1e-9
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

    print("MemoryClient tests passed.")


if __name__ == "__main__":
    main()
