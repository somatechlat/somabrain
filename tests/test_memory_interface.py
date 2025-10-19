import os
import asyncio

os.environ.setdefault("DISABLE_START_SERVER", "1")

from somabrain.interfaces.memory import MemoryBackend
from somabrain.services.memory_service import MemoryService


class DummyBackend:
    def __init__(self):
        self.store = {}

    def remember(self, key: str, payload: dict, *args, **kwargs):
        coord = (0.0, 0.0, 0.0)
        self.store[key] = dict(payload)
        self.store[key]["coordinate"] = coord
        return coord

    async def aremember(self, key: str, payload: dict, *args, **kwargs):
        return self.remember(key, payload, *args, **kwargs)

    def link(
        self, from_coord, to_coord, link_type: str = "related", weight: float = 1.0
    ):
        # no-op
        return None

    async def alink(
        self, from_coord, to_coord, link_type: str = "related", weight: float = 1.0
    ):
        return None

    def coord_for_key(self, key: str, universe: str | None = None):
        return self.store.get(key, {}).get("coordinate")

    def payloads_for_coords(self, coords, universe: str | None = None):
        out = []
        for k, v in self.store.items():
            if v.get("coordinate") in coords:
                out.append(v)
        return out

    def delete(self, coordinate):
        # remove first matching
        for k, v in list(self.store.items()):
            if v.get("coordinate") == coordinate:
                del self.store[k]
                return True
        return False

    def links_from(self, start, type_filter: str | None = None, limit: int = 50):
        return []


def test_memory_service_with_protocol():
    backend: MemoryBackend = DummyBackend()
    svc = MemoryService(backend, namespace="test")
    coord = svc.remember("k1", {"task": "t1"})
    assert coord == (0.0, 0.0, 0.0)
    # recall via payloads_for_coords
    payloads = svc.payloads_for_coords([coord])
    assert isinstance(payloads, list)
    assert payloads[0]["task"] == "t1"


def test_async_remember_event_loop():
    backend = DummyBackend()
    svc = MemoryService(backend, namespace="test")

    async def run():
        c = await svc.aremember("k2", {"task": "t2"})
        assert c == (0.0, 0.0, 0.0)

    asyncio.run(run())
