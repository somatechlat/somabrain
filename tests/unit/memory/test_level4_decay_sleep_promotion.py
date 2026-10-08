"""Level 4 — decay / recency / sleep consolidation behavioural tests.

Production implementations only (no mocks, no source greps):
- ``somabrain.math.recency.stretched_exponential_recency``
- ``somabrain.context.builder.ContextBuilder`` temporal decay / proximity score
- ``somabrain.memory.promotion.WMLTMPromoter`` (real MemoryClient over real HTTP)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest

pytestmark = pytest.mark.no_django

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _unit_settings import configure_unit_settings  # noqa: E402

configure_unit_settings()


# ---------------------------------------------------------------------------
# Real local HTTP memory service (stdlib). Production ``MemoryClient`` talks to
# it over real HTTP — this is a live store, not a test double of the client.
# ---------------------------------------------------------------------------


class _LtmHttpService:
    def __init__(self) -> None:
        self.memories: dict[str, dict[str, Any]] = {}
        self.links: list[dict[str, Any]] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.base_url = ""

    def start(self) -> str:
        service = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: Any) -> None:
                return

            def _json(self, status: int, obj: Any) -> None:
                data = json.dumps(obj).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:  # noqa: N802
                if self.path in ("/health", "/healthz", "/readyz"):
                    self._json(200, {"ok": True})
                    return
                if self.path.startswith("/memories/"):
                    coord = unquote(self.path[len("/memories/") :])
                    mem = service.memories.get(coord)
                    if mem is None:
                        self._json(404, {"error": "not found"})
                    else:
                        self._json(200, {"memory": dict(mem), "coord": coord})
                    return
                self._json(404, {"error": "unknown path"})

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    self._json(400, {"error": "bad json"})
                    return
                if self.path == "/memories":
                    coord = str(body.get("coord") or "")
                    payload = dict(body.get("payload") or {})
                    payload.setdefault("coord", coord)
                    if body.get("tenant_id") is not None:
                        payload.setdefault("tenant_id", body["tenant_id"])
                    service.memories[coord] = payload
                    self._json(200, {"coord": coord, "memory": dict(payload)})
                    return
                if self.path == "/graph/link":
                    service.links.append(dict(body))
                    self._json(200, {"ok": True})
                    return
                self._json(404, {"error": "unknown path"})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="ltm-http", daemon=True
        )
        self._thread.start()
        host, port = self._server.server_address[:2]
        self.base_url = f"http://{host}:{port}"
        return self.base_url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


@contextlib.contextmanager
def live_ltm():
    svc = _LtmHttpService()
    url = svc.start()
    try:
        yield svc, url
    finally:
        svc.stop()


class _ClientCfg:
    """Config object carrying the live LTM endpoint and Brain→SFM token."""

    def __init__(self, base_url: str) -> None:
        self.SOMA_API_TOKEN = "test-sfm-token"
        self.soma_api_token = "test-sfm-token"
        self.memory_http_endpoint = base_url
        self.MEMORY_HTTP_ENDPOINT = base_url
        self.namespace = "somabrain:default:l4"
        self.tenant = "default"


def _client(base_url: str):
    from somabrain.memory.client import MemoryClient

    return MemoryClient(
        cfg=_ClientCfg(base_url),
        namespace="somabrain:default:l4",
        tenant="default",
    )


# ---------------------------------------------------------------------------
# Recency kernel
# ---------------------------------------------------------------------------


class TestRecencyKernel:
    def test_age_zero_is_high_age_infinite_is_floor(self) -> None:
        from somabrain.math.contracts import (
            RECENCY_FLOOR,
            RECENCY_SCALE,
            RECENCY_SHARPNESS,
        )
        from somabrain.math.recency import stretched_exponential_recency

        kwargs = dict(
            scale=RECENCY_SCALE, sharpness=RECENCY_SHARPNESS, floor=RECENCY_FLOOR
        )
        at_zero = stretched_exponential_recency(0.0, **kwargs)
        at_small = stretched_exponential_recency(1.0, **kwargs)
        at_huge = stretched_exponential_recency(1e9, **kwargs)
        assert at_zero == pytest.approx(1.0)
        assert at_zero >= at_small >= at_huge
        assert at_huge == pytest.approx(RECENCY_FLOOR)
        assert at_small < 1.0

    def test_nan_age_is_floor_not_one(self) -> None:
        from somabrain.math.contracts import (
            RECENCY_FLOOR,
            RECENCY_SCALE,
            RECENCY_SHARPNESS,
        )
        from somabrain.math.recency import stretched_exponential_recency

        val = stretched_exponential_recency(
            float("nan"),
            scale=RECENCY_SCALE,
            sharpness=RECENCY_SHARPNESS,
            floor=RECENCY_FLOOR,
        )
        assert val == pytest.approx(RECENCY_FLOOR)
        assert val != 1.0
        assert math.isfinite(val)

    def test_monotone_decay_with_age(self) -> None:
        from somabrain.math.contracts import (
            RECENCY_FLOOR,
            RECENCY_SCALE,
            RECENCY_SHARPNESS,
        )
        from somabrain.math.recency import stretched_exponential_recency

        ages = [0.0, 1.0, 10.0, 60.0, 600.0, 6000.0, 1e6]
        vals = [
            stretched_exponential_recency(
                a,
                scale=RECENCY_SCALE,
                sharpness=RECENCY_SHARPNESS,
                floor=RECENCY_FLOOR,
            )
            for a in ages
        ]
        for earlier, later in zip(vals, vals[1:], strict=False):
            assert later <= earlier + 1e-12
        assert vals[0] == pytest.approx(1.0)
        assert vals[-1] == pytest.approx(RECENCY_FLOOR)


# ---------------------------------------------------------------------------
# Proximity decay — older = lower score under equal content
# ---------------------------------------------------------------------------


class TestProximityDecay:
    def test_older_timestamp_scores_lower_under_equal_content(self) -> None:
        from somabrain.context.builder import ContextBuilder, MemoryRecord

        builder = ContextBuilder(embed_fn=lambda _q: [1.0, 0.0, 0.0], memory={})
        now = time.time()
        # Identical embedding and graph score; only age differs.
        recent = MemoryRecord(
            id="recent",
            score=0.0,
            metadata={"timestamp": now - 1.0, "graph_score": 0.5},
            embedding=[1.0, 0.0, 0.0],
        )
        old = MemoryRecord(
            id="old",
            score=0.0,
            metadata={"timestamp": now - 3600.0, "graph_score": 0.5},
            embedding=[1.0, 0.0, 0.0],
        )
        weights = builder._compute_weights([1.0, 0.0, 0.0], [recent, old])
        assert weights[0] > weights[1], (
            f"recent must outrank old under equal content: {weights}"
        )

    def test_temporal_decay_matches_recency_floor_at_infinity(self) -> None:
        from somabrain.context.builder import ContextBuilder
        from somabrain.math.contracts import RECENCY_FLOOR

        builder = ContextBuilder(embed_fn=lambda _q: [1.0], memory={})
        assert builder._temporal_decay(0.0) <= 1.0
        assert builder._temporal_decay(time.time()) == pytest.approx(1.0, abs=0.05)
        assert builder._temporal_decay(time.time() - 1e9) == pytest.approx(
            RECENCY_FLOOR
        )


# ---------------------------------------------------------------------------
# Sleep / consolidation: promotion sync_to_async does not deadlock
# WM→LTM promote: item appears in LTM after promotion
# ---------------------------------------------------------------------------


class TestPromotionSleepConsolidation:
    def test_promote_item_appears_in_ltm_and_sync_path_completes(self) -> None:
        """Promotion stores the item in LTM and the sync_to_async path finishes.

        ``graph_client`` is set so ``promote`` must leave the async context via
        ``sync_to_async`` for the link write. A hang here is a deadlock.
        """
        with live_ltm() as (svc, url):
            from somabrain.memory.promotion import WMLTMPromoter

            client = _client(url)
            promoter = WMLTMPromoter(
                memory_client=client,
                graph_client=client,
                tenant_id="l4_promote",
                threshold=0.85,
                min_ticks=3,
            )

            item_id = "wm-item-1"
            vector = [0.1, 0.2, 0.3]
            payload = {"content": "salient fact", "task": "remember this"}
            wm_coordinate = (0.1, 0.2, 0.3)

            async def _tick(tick: int, salience: float):
                return await asyncio.wait_for(
                    promoter.check_and_promote(
                        item_id=item_id,
                        salience=salience,
                        tick=tick,
                        vector=vector,
                        payload=payload,
                        wm_coordinate=wm_coordinate,
                    ),
                    timeout=5.0,
                )

            # Ticks 1–2: candidate only; tick 3: promote (PROMOTE_TICKS=3)
            assert asyncio.run(_tick(1, 0.90)) is None
            assert asyncio.run(_tick(2, 0.92)) is None
            result = asyncio.run(_tick(3, 0.91))
            assert result is not None
            assert result.promoted is True, result.error
            assert result.ltm_coordinate is not None

            # A2.2 — promoted item retains LTM coordinate reference
            assert promoter.get_ltm_reference(item_id) == result.ltm_coordinate

            # Item actually present in LTM behind the real client
            stored = client.fetch_by_coord(result.ltm_coordinate)
            assert stored is not None
            assert stored.get("promoted_from_wm") is True
            assert stored.get("memory_type") == "episodic"
            assert stored.get("original_wm_id") == item_id
            assert stored.get("content") == "salient fact"

            # Real HTTP store holds the record (not just the in-process ref)
            coord_str = (
                f"{result.ltm_coordinate[0]},"
                f"{result.ltm_coordinate[1]},"
                f"{result.ltm_coordinate[2]}"
            )
            assert coord_str in svc.memories
            assert svc.memories[coord_str].get("original_wm_id") == item_id

    def test_promotion_sync_to_async_completes_within_deadlock_budget(self) -> None:
        """The graph-link write under sync_to_async must finish, not hang."""
        with live_ltm() as (_svc, url):
            from somabrain.memory.promotion import WMLTMPromoter

            client = _client(url)
            promoter = WMLTMPromoter(
                memory_client=client,
                graph_client=client,
                tenant_id="l4_deadlock",
                threshold=0.85,
                min_ticks=1,
            )

            async def _one_shot():
                return await asyncio.wait_for(
                    promoter.promote(
                        "wm-deadlock",
                        [0.0, 1.0, 0.0],
                        {"content": "x"},
                        wm_coordinate=(0.0, 1.0, 0.0),
                    ),
                    timeout=5.0,
                )

            start = time.perf_counter()
            result = asyncio.run(_one_shot())
            elapsed = time.perf_counter() - start
            assert result.promoted is True
            assert elapsed < 5.0

    def test_check_and_promote_respects_min_ticks_contract(self) -> None:
        from somabrain.math.contracts import PROMOTE_THETA, PROMOTE_TICKS
        from somabrain.memory.promotion import PromotionTracker

        tracker = PromotionTracker(
            threshold=PROMOTE_THETA,
            min_ticks=PROMOTE_TICKS,
            tenant_id="l4_ticks",
        )
        item = "tick-item"
        assert tracker.check(item, salience=0.99, tick=1) is False
        assert tracker.check(item, salience=0.99, tick=2) is False
        assert tracker.check(item, salience=0.99, tick=3) is True
        tracker.mark_promoted(item)
        assert tracker.check(item, salience=0.99, tick=4) is False
