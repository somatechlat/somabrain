"""Oak Planner Module
=======================

This module provides a very simple planning capability for the Oak feature. The
goal is to expose a deterministic, test‑friendly API that can be used by the
FastAPI route ``/oak/plan`` (to be added later) and by internal services.

The implementation purposefully avoids any heavy‑weight graph traversal – the
core ROAMDP roadmap only requires the ability to return a ranked list of option
identifiers for a given tenant. The ranking is based on the ``utility`` value
computed when an :class:`~somabrain.oak.option_manager.Option` is created.

All configuration values (such as the default number of options to return) are
read from the global ``settings`` instance, ensuring there are no hard‑coded
magic numbers, in line with the VIBE coding rules.
"""

from __future__ import annotations

from typing import List

from common.config.settings import settings
from somabrain.cognitive.thread_model import CognitiveThread

__all__ = ["plan_for_tenant"]


def plan_for_tenant(tenant_id: str, max_options: int | None = None) -> List[str]:
    """Return a utility‑ranked list of option IDs for a specific tenant.

    Parameters
    ----------
    tenant_id: str
        Tenant whose options should be considered.
    max_options: int | None, optional
        Upper bound on the number of IDs returned. If ``None`` the value is read
        from ``settings.OAK_PLAN_MAX_OPTIONS`` (default ``10``).

    Returns
    -------
    List[str]
        Option identifiers sorted by descending utility, limited to ``max_options``.
    """
    default_max = getattr(settings, "OAK_PLAN_MAX_OPTIONS", 10)
    limit = max_options if max_options is not None else default_max

    # First, attempt to use a Cognitive Thread if enabled and present.
    # NOTE: ``get_session_factory`` is imported lazily to honour monkey‑patches
    # performed in the test suite. Importing it at module load time would bind
    # the original function object, causing the monkey‑patched version to be
    # ignored. By importing inside the function we ensure the latest attribute
    # value from ``somabrain.storage.db`` is used.
    try:
        from somabrain.storage.db import (
            get_session_factory,
        )  # pylint: disable=import-outside-toplevel

        Session = get_session_factory()
        with Session() as session:
            thread = session.get(CognitiveThread, tenant_id)
            if thread:
                nxt = thread.next_option()
                if nxt:
                    # Persist cursor advancement.
                    session.commit()
                    return [nxt]
    except Exception:
        # Any failure (e.g., missing table) falls back to utility ranking.
        pass

    # Retrieve only the tenant's options and sort by utility (high → low).
    # Import lazily to avoid side‑effects during module import (MemoryClient init).
    try:
        from .option_manager import (
            option_manager,
        )  # pylint: disable=import-outside-toplevel

        options = option_manager.list_options(tenant_id)
    except Exception:
        # If the option manager cannot be imported (e.g., missing cfg), fallback to empty list.
        options = []
    sorted_opts = sorted(
        options, key=lambda o: getattr(o, "utility", 0.0), reverse=True
    )
    return [opt.option_id for opt in sorted_opts[:limit]]
