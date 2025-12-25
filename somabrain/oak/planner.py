"""Oak Planner Module
=======================

This module provides a very simple planning capability for the Oak feature. The
goal is to expose a deterministic, test‑friendly API that can be used by the
Django Ninja route ``/oak/plan`` (to be added later) and by internal services.

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

from django.conf import settings
from somabrain.models import CognitiveThread

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

    Fallback Behavior:
        1. First attempts to use CognitiveThread from database for cursor-based
           option selection. If database is unavailable, falls through.
        2. Then attempts to use option_manager for utility-ranked options.
           If option_manager fails (e.g., missing config), returns empty list.

        The empty list fallback is intentional: planning should not block
        application startup or cause errors when Oak subsystem is not configured.
        Callers should handle empty results gracefully.
    """
    default_max = getattr(settings, "OAK_PLAN_MAX_OPTIONS", 10)
    limit = max_options if max_options is not None else default_max

    # First, attempt to use a Cognitive Thread if enabled and present.
    # Uses Django ORM for database access.
    try:
        # Django ORM replacement
        thread = CognitiveThread.objects.filter(pk=tenant_id).first()
        if thread:
            nxt = thread.next_option()
            if nxt:
                # Persist cursor advancement.
                thread.save()
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
