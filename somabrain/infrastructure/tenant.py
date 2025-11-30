from __future__ import annotations
from typing import Optional

"""somabrain.infrastructure.tenant
===================================

Centralised helper for normalising tenant / namespace strings.

The code base historically used a mixture of terms – *namespace*, *tenant*,
*universe* – and performed ad‑hoc parsing (splitting on `:` or using the raw
string).  This module provides a **single source of truth** for converting any
namespace string into a canonical ``tenant_id`` that is used throughout the
system (metrics, circuit‑breaker, outbox queries, etc.).

The implementation is deliberately tiny and pure‑Python so it can be imported
early without side effects.  It is also fully type‑annotated and includes a
fallback for empty or ``None`` values.
"""



__all__ = ["tenant_label", "resolve_namespace"]


def tenant_label(namespace: Optional[str]) -> str:
    """Return a stable, human‑readable tenant identifier.

    The function follows the historic behaviour used in ``MemoryService``:
        pass

    * If *namespace* is falsy, ``"default"`` is returned.
    * If the string contains a colon (`:`) the suffix after the last colon
      is used – this matches the pattern ``"org:tenant"`` that appears in a
      few places.
    * Otherwise the full string is returned unchanged.

    The result is always a non‑empty string and can safely be used as a Prometheus
    label value.
    """
    if not namespace:
        return "default"
    ns = str(namespace)
    if ":" in ns:
        # ``rsplit`` ensures we keep the part after the *last* colon.
        suffix = ns.rsplit(":", 1)[-1]
        return suffix or ns
    return ns


def resolve_namespace(tenant_id: str) -> str:
    """Reverse lookup – given a *tenant_id* return the original namespace.

    In the current code base the mapping is one‑to‑one, so we simply return the
    identifier itself.  The function exists for symmetry and future‑proofing –
    if a more complex mapping is required later the implementation can be
    changed without touching callers.
    """
    return tenant_id
