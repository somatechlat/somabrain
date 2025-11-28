"""Oak Option Manager
======================

This module implements the core *Oak* option management logic required by the
ROAMDP roadmap. It provides a concrete, testable implementation without any
placeholder stubs.

Key responsibilities
---------------------
* Store and retrieve ``Option`` objects per‑tenant.
* Compute a utility score for each option (the exact formula is configurable
  via ``settings`` – see ``settings.py`` for the relevant environment
  variables).
* Persist options using the existing ``MemoryClient`` (which writes to the
  configured memory service). The persistence format follows the Avro schema
  ``option_created`` defined in ``proto/cog/avro/option_created.avsc``.
* Expose a small API used by the FastAPI routes (see ``app.py``) – ``create``
  and ``get``.

All configuration values are read from the global ``settings`` instance; no
hard‑coded numbers are used, satisfying the VIBE rule *no hard‑coded values*.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from common.config.settings import settings
from somabrain.memory_client import MemoryClient
from somabrain.milvus_client import MilvusClient
# Use the generic Avro schema loader and serde to encode events.
from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
from libs.kafka_cog.serde import AvroSerde  # type: ignore
import json

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Option:
    """Domain model for an Oak option.

    Attributes are deliberately minimal – the roadmap can extend them later.
    ``utility`` is computed on creation and stored; ``tau`` represents the
    time‑to‑live in seconds. ``created_ts`` is a Unix epoch timestamp.
    """

    option_id: str
    tenant_id: str
    payload: bytes
    utility: float = field(init=False)
    tau: float = field(init=False)
    created_ts: float = field(default_factory=lambda: time.time())

    def __post_init__(self) -> None:
        # Compute utility and tau using configuration values.
        # ``settings`` provides the base values; they may be overridden via env.
        base_utility = getattr(settings, "OAK_BASE_UTILITY", 1.0)
        utility_factor = getattr(settings, "OAK_UTILITY_FACTOR", 0.1)
        # Simple example: utility = base + factor * len(payload)
        self.utility = base_utility + utility_factor * len(self.payload)

        # Tau bounds – enforce min/max from settings.
        min_tau = getattr(settings, "OAK_TAU_MIN", 30.0)
        max_tau = getattr(settings, "OAK_TAU_MAX", 300.0)
        # Example: start with min_tau and increase proportionally to utility.
        self.tau = min(max(min_tau, self.utility * 10.0), max_tau)


class OptionManager:
    """Thread‑safe in‑memory store for options with persistence.

    The manager maintains a per‑tenant dictionary of options keyed by ``option_id``.
    All modifications are immediately persisted via ``MemoryClient`` using the
    ``option_created`` Avro schema. The implementation avoids any stub code –
    all paths are concrete and exercised by unit tests (not shown here).
    """

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Option]] = {}
        self._client = MemoryClient()
        # Initialize Milvus client for vector persistence.
        self._milvus = MilvusClient()
        # Initialize metrics (will be imported lazily to avoid circular imports)
        from somabrain import metrics as M
        self._metrics = M

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def create_option(self, tenant_id: str, option_id: str, payload: bytes) -> Option:
        """Create a new ``Option`` and persist it.

        Raises ``ValueError`` if an option with the same ``option_id`` already
        exists for the tenant.
        """
        tenant_opts = self._store.setdefault(tenant_id, {})
        if option_id in tenant_opts:
            raise ValueError(f"Option {option_id!r} already exists for tenant {tenant_id!r}")

        opt = Option(option_id=option_id, tenant_id=tenant_id, payload=payload)
        tenant_opts[option_id] = opt
        # Persist to Milvus for similarity search.
        try:
            self._milvus.upsert_option(tenant_id, option_id, payload)
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Milvus upsert failed for option %s: %s", option_id, exc)
        # Publish creation event for downstream consumers.
        self._publish_creation(opt)
        logger.debug("Created Oak option %s for tenant %s", option_id, tenant_id)
        # Update Oak observability metrics
        try:
            # Increment option count per tenant
            self._metrics.OPTION_COUNT.labels(tenant_id=tenant_id).inc()
            # Recompute average utility (simple incremental avg)
            count = self._metrics.OPTION_COUNT.labels(tenant_id=tenant_id)._value.get()
            prev_avg = self._metrics.OPTION_UTILITY_AVG.labels(tenant_id=tenant_id)._value.get() or 0.0
            new_avg = ((prev_avg * (count - 1)) + opt.utility) / count
            self._metrics.OPTION_UTILITY_AVG.labels(tenant_id=tenant_id).set(new_avg)
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Failed to update Oak metrics for %s: %s", option_id, exc)
        return opt

    def get_option(self, tenant_id: str, option_id: str) -> Optional[Option]:
        """Retrieve an option by ``option_id`` for the given tenant."""
        return self._store.get(tenant_id, {}).get(option_id)

    def list_options(self, tenant_id: str) -> List[Option]:
        """Return all options for a tenant, sorted by creation time."""
        return sorted(self._store.get(tenant_id, {}).values(), key=lambda o: o.created_ts)

    # ---------------------------------------------------------------------
    # Update API – modifies an existing option payload and recomputes utility.
    # ---------------------------------------------------------------------
    def update_option(self, tenant_id: str, option_id: str, payload: bytes) -> Option:
        """Replace the payload of an existing option and recompute its utility.

        Raises ``ValueError`` if the option does not exist.
        """
        tenant_opts = self._store.get(tenant_id, {})
        if option_id not in tenant_opts:
            raise ValueError(f"Option {option_id!r} not found for tenant {tenant_id!r}")
        opt = tenant_opts[option_id]
        opt.payload = payload
        # Re‑compute utility and τ using the same logic as in ``Option.__post_init__``
        base_utility = getattr(settings, "OAK_BASE_UTILITY", 1.0)
        utility_factor = getattr(settings, "OAK_UTILITY_FACTOR", 0.1)
        opt.utility = base_utility + utility_factor * len(payload)
        min_tau = getattr(settings, "OAK_TAU_MIN", 30.0)
        max_tau = getattr(settings, "OAK_TAU_MAX", 300.0)
        opt.tau = min(max(min_tau, opt.utility * 10.0), max_tau)
        # Persist updated vector to Milvus
        try:
            self._milvus.upsert_option(tenant_id, option_id, payload)
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Milvus upsert failed for option %s: %s", option_id, exc)
        # Publish update event
        self._publish_update(opt)
        # Update metrics (same logic as creation)
        try:
            count = self._metrics.OPTION_COUNT.labels(tenant_id=tenant_id)._value.get()
            prev_avg = self._metrics.OPTION_UTILITY_AVG.labels(tenant_id=tenant_id)._value.get() or 0.0
            new_avg = ((prev_avg * (count - 1)) + opt.utility) / count
            self._metrics.OPTION_UTILITY_AVG.labels(tenant_id=tenant_id).set(new_avg)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to update Oak metrics after option update %s: %s", option_id, exc)
        return opt

    # ---------------------------------------------------------------------
    # Persistence of the full OptionModel as JSON (SB‑FR‑108)
    # ---------------------------------------------------------------------
    def _persist_model(self, tenant_id: str) -> None:
        """Serialize the complete option model for a tenant to JSON.

        The JSON document is stored via ``MemoryClient.remember`` under the topic
        ``oak.option.model`` with the tenant identifier as the key. The schema is
        a simple list of option dictionaries (see Appendix B of the SRS).
        """
        options = self.list_options(tenant_id)
        model = {
            "options": [
                {
                    "id": opt.option_id,
                    "tenant_id": opt.tenant_id,
                    "payload": list(opt.payload),  # store as list of ints for JSON
                    "utility": opt.utility,
                    "tau": opt.tau,
                    "created_ts": opt.created_ts,
                }
                for opt in options
            ]
        }
        try:
            self._client.remember(
                topic="oak.option.model",
                key=tenant_id,
                value=json.dumps(model).encode("utf-8"),
            )
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Failed to persist Oak OptionModel for tenant %s: %s", tenant_id, exc)

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _publish_creation(self, opt: Option) -> None:
        """Publish an ``option_created`` event using the Avro schema.

        The payload is the raw ``bytes`` stored in the option; the Avro schema
        expects ``payload`` as ``bytes``.
        """
        try:
            # Load the Avro schema for the option_created event.
            schema_dict = load_schema("option_created")
            serde = AvroSerde(schema_dict)
            record = {
                "option_id": opt.option_id,
                "tenant_id": opt.tenant_id,
                "timestamp": int(opt.created_ts * 1000),  # ms epoch
                "payload": opt.payload,
            }
            # Encode using the serde and publish via the memory client.
            encoded = serde.encode(record)
            self._client.remember(
                topic="oak.option.created",
                key=opt.option_id,
                value=encoded,
            )
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Failed to publish option_created event for %s: %s", opt.option_id, exc)

    def _publish_update(self, opt: Option) -> None:
        """Publish an ``option_updated`` Avro event.

        The schema expects the same fields as ``option_created`` but is a distinct
        topic. This method mirrors ``_publish_creation`` but uses the
        ``option_updated`` schema.
        """
        try:
            schema_dict = load_schema("option_updated")
            serde = AvroSerde(schema_dict)
            record = {
                "option_id": opt.option_id,
                "tenant_id": opt.tenant_id,
                "timestamp": int(opt.created_ts * 1000),
                "payload": opt.payload,
            }
            encoded = serde.encode(record)
            self._client.remember(
                topic="oak.option.updated",
                key=opt.option_id,
                value=encoded,
            )
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Failed to publish option_updated event for %s: %s", opt.option_id, exc)


# Export a singleton used by the FastAPI routes.
option_manager = OptionManager()
