"""
Memory Service Module for SomaBrain

This module provides a high-level service layer for memory operations in SomaBrain.
It wraps the MultiTenantMemory client with additional helpers for universe scoping,
asynchronous operations, and cleaner API integration.

Key Features:
- Universe-aware memory operations
- Synchronous and asynchronous memory access
- Link management between memories
- Coordinate-based memory retrieval
- Namespace isolation through service wrapper

        return cls._circuit_breaker.should_attempt_reset(tenant)
                    gauge.labels(tenant_id=str(tenant_label)).set(count)
                else:
                    # Fallback to unlabeled gauge (legacy behavior)
                    if tenant_label == "default":
                        gauge.set(count)
            except Exception:
                pass

    def remember(self, key: str, payload: dict, universe: str | None = None):
        """Stores a memory payload. In V3, this fails fast if the remote is down."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")

        try:
            result = self.client().remember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember(self, key: str, payload: dict, universe: str | None = None):
        """Async version of remember."""
        if universe and "universe" not in payload:
            payload["universe"] = universe

        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")

        try:
            result = await self.client().aremember(key, payload)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict]],
        universe: str | None = None,
    ) -> list[tuple[float, float, float]]:
        """Store multiple memory payloads in a single operation."""

        prepared: list[tuple[str, dict]] = []
        for key, payload in items:
            body = dict(payload)
            if universe and "universe" not in body:
                body["universe"] = universe
            prepared.append((key, body))

        if not prepared:
            return []

        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")

        try:
            coords = await self.client().aremember_bulk(prepared)
            self._mark_success()
            return list(coords)
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    def link(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Create a link between memories (fail-fast)."""
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            result = self.client().link(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    async def alink(self, from_coord, to_coord, link_type="related", weight=1.0):
        """Async version of link."""
        if self._is_circuit_open():
            raise RuntimeError("Memory service unavailable (circuit open)")
        try:
            result = await self.client().alink(from_coord, to_coord, link_type, weight)
            self._mark_success()
            return result
        except Exception as e:
            self._mark_failure()
            raise RuntimeError("Memory service unavailable") from e

    def _health_check(self) -> bool:
        try:
            health = self.client().health()
        except Exception:
            return False
        if isinstance(health, dict):
            if "http" in health:
                return bool(health.get("http"))
            return bool(health.get("ok"))
        return False

    def _reset_circuit_if_needed(self) -> bool:
        """Attempt to close the circuit breaker if enough time has elapsed.

        The logic is now delegated to the shared :class:`CircuitBreaker`
        instance.  If the breaker signals that a reset attempt is allowed and the
        health check passes, we record a successful request which clears the
        circuit state.
        """
        if not self._is_circuit_open():
            return False
        tenant = getattr(self, "namespace", "default")
        breaker = self.__class__._circuit_breaker
        if not breaker.should_attempt_reset(tenant):
            return False
        if self._health_check():
            breaker.record_success(tenant)
            return True
        # No state change – the circuit remains open.
        return False

    # Journal/outbox alternative removed: no background replay

    def coord_for_key(self, key: str, universe: str | None = None):
        return self.client().coord_for_key(key, universe)

    def payloads_for_coords(self, coords, universe: str | None = None):
        return self.client().payloads_for_coords(coords, universe)

    def delete(self, coordinate):
        return self.client().delete(coordinate)

    def links_from(self, start, type_filter: str | None = None, limit: int = 50):
        return self.client().links_from(start, type_filter, limit)

# The functional ``MemoryService`` class is now defined directly above, so no
# re‑export is required.  Removing the previous alias prevents an ``AttributeError``
# where callers received the inner class without the public methods.
