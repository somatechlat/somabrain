"""Multi-tenant memory pool for SomaBrain.

The pool hands out `MemoryClient` instances per namespace and replays journal
entries so each client sees consistent context even before the external memory
service is reachable. When the HTTP service is down the pool relies on the
client's stub mirror.
"""

from __future__ import annotations

import logging
from typing import Dict

from .config import Config
from .journal import iter_events
from .memory_client import MemoryClient


class MultiTenantMemory:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._pool: Dict[str, MemoryClient] = {}

    def for_namespace(self, namespace: str) -> MemoryClient:
        ns = str(namespace)
        if ns not in self._pool:
            # clone config with namespace override
            from dataclasses import replace

            cfg2 = replace(self.cfg)
            cfg2.namespace = ns
            try:
                client = MemoryClient(cfg2)
                logging.getLogger(__name__).debug(
                    "create client in pool %s %s", ns, id(client)
                )
                # On first creation, replay journal for this namespace so the
                # process-local outbox/mirror is seeded. The memory service
                # should deduplicate events; replaying into an HTTP-backed client is
                # still useful for bootstrapping and local visibility.
                if bool(getattr(cfg2, "persistent_journal_enabled", False)):
                    try:
                        for ev in iter_events(
                            str(getattr(cfg2, "journal_dir", "./data/somabrain")), ns
                        ):
                            et = str(ev.get("type") or "")
                            if et == "mem":
                                key = str(ev.get("key") or ev.get("task") or "payload")
                                payload = dict(ev.get("payload") or {})
                                client.remember(key, payload)
                            elif et == "link":
                                fc = ev.get("from") or ev.get("from_coord")
                                tc = ev.get("to") or ev.get("to_coord")
                                if (
                                    isinstance(fc, (list, tuple))
                                    and isinstance(tc, (list, tuple))
                                    and len(fc) == 3
                                    and len(tc) == 3
                                ):
                                    ltype = str(
                                        ev.get("link_type")
                                        or ev.get("type")
                                        or "related"
                                    )
                                    w = float(ev.get("weight") or 1.0)
                                    client.link(
                                        (float(fc[0]), float(fc[1]), float(fc[2])),
                                        (float(tc[0]), float(tc[1]), float(tc[2])),
                                        link_type=ltype,
                                        weight=w,
                                    )
                    except Exception:
                        pass
                self._pool[ns] = client
            except Exception:
                # Creation failed (e.g., httpx import error). Create a client
                # anyway (it will operate in offline mode: outbox + mirrors).
                logging.getLogger(__name__).exception(
                    "memory client creation failed, creating offline client"
                )
                client = MemoryClient(cfg2)
                # Replay journal in stub mode as well
                if bool(getattr(cfg2, "persistent_journal_enabled", False)):
                    try:
                        for ev in iter_events(
                            str(getattr(cfg2, "journal_dir", "./data/somabrain")), ns
                        ):
                            et = str(ev.get("type") or "")
                            if et == "mem":
                                key = str(ev.get("key") or ev.get("task") or "payload")
                                payload = dict(ev.get("payload") or {})
                                client.remember(key, payload)
                            elif et == "link":
                                fc = ev.get("from") or ev.get("from_coord")
                                tc = ev.get("to") or ev.get("to_coord")
                                if (
                                    isinstance(fc, (list, tuple))
                                    and isinstance(tc, (list, tuple))
                                    and len(fc) == 3
                                    and len(tc) == 3
                                ):
                                    ltype = str(
                                        ev.get("link_type")
                                        or ev.get("type")
                                        or "related"
                                    )
                                    w = float(ev.get("weight") or 1.0)
                                    client.link(
                                        (float(fc[0]), float(fc[1]), float(fc[2])),
                                        (float(tc[0]), float(tc[1]), float(tc[2])),
                                        link_type=ltype,
                                        weight=w,
                                    )
                    except Exception:
                        pass
                self._pool[ns] = client
        return self._pool[ns]
