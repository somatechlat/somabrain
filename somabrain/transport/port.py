"""BrainPort — the one seam between a caller and SomaBrain.

One core, two adapters (PLAN §1): the deployment mode selects a binding and the
caller never learns which one it got. ``BrainPort`` is a Protocol so the core
can be exercised against any implementation — including a pure in-process one
in tests — without importing gRPC, HTTP, or Django into the cognitive trees.

Binding selection is fail-closed (VIBE Rule 91). A deployment mode that is
unset or unrecognised raises; it is never folded into a default. The two
modes and their transports are:

======  =========================  ===========================================
Mode    Binding                    Gate
======  =========================  ===========================================
LOCAL   gRPC over a Unix socket    filesystem permissions on the socket
        (``/run/soma/brain.sock``)  (mode 0600). No bearer is issued.
NET     gRPC over TCP + HTTP/2     TLS 1.3 (RFC 8446) peer certificates
        (RFC 9113)                  validated per RFC 5280 §6, plus the
                                    service token from Vault. An absent
                                    credential is a refusal, not a blank.
======  =========================  ===========================================
"""

from __future__ import annotations

import enum
from collections.abc import AsyncIterator, Sequence
from typing import Protocol, runtime_checkable

from somabrain.proto.brain_pb2 import (
    ForgetRequest,
    HealthRequest,
    MemoryWrite,
    RecallBatchRequest,
    RecallRequest,
    RememberBatchRequest,
    RememberRequest,
    StreamContextRequest,
)


class TransportBinding(str, enum.Enum):
    """Which wire the brain is reached over."""

    LOCAL = "LOCAL"
    NET = "NET"


class TransportConfigurationError(RuntimeError):
    """Raised when the deployment mode or its binding settings are unusable.

    Fail-closed (VIBE Rule 91): never guess a binding, never fall back to
    localhost, never continue without the credential a binding requires.
    """


# The one directory both sockets live in. A single compose volume mount
# (``soma_run:/run/soma``) carries the whole local bus.
RUN_DIR = "/run/soma"
BRAIN_SOCK = f"{RUN_DIR}/brain.sock"
SFM_SOCK = f"{RUN_DIR}/sfm.sock"

# Accepted spellings for each binding. Everything else raises.
_MODE_ALIASES: dict[str, TransportBinding] = {
    "LOCAL": TransportBinding.LOCAL,
    "STANDALONE": TransportBinding.LOCAL,
    "NET": TransportBinding.NET,
    "DISTRIBUTED": TransportBinding.NET,
}


def resolve_binding(mode: str | None) -> TransportBinding:
    """Map a deployment mode string onto a transport binding.

    Args:
        mode: The configured deployment mode (e.g. ``SA01_DEPLOYMENT_MODE``).

    Returns:
        The transport binding for that mode.

    Raises:
        TransportConfigurationError: If ``mode`` is empty or unrecognised. An
            unrecognised mode is refused rather than folded into LOCAL or NET.
    """
    key = (mode or "").strip().upper()
    if not key:
        raise TransportConfigurationError(
            "deployment mode is not set; refusing to guess a transport binding. "
            "Set SA01_DEPLOYMENT_MODE to LOCAL (Unix socket) or NET (TCP/TLS)."
        )
    binding = _MODE_ALIASES.get(key)
    if binding is None:
        raise TransportConfigurationError(
            f"unrecognised deployment mode {mode!r}; expected one of "
            f"{sorted(_MODE_ALIASES)} (aliases STANDALONE/DISTRIBUTED accepted). "
            "Refusing to guess a transport binding."
        )
    return binding


@runtime_checkable
class BrainPort(Protocol):
    """Every call between a caller and the brain.

    Implementations must be fail-closed: a transport that cannot reach the
    brain raises. It never returns an empty recall to mean "unreachable" —
    that is the MemoryRecallUnavailable contract in
    ``services/common/memory_contract.py`` and an outage must surface as an
    outage (R-05 / F-10).
    """

    async def remember(self, write: MemoryWrite) -> list:
        """Store one memory; return one ack per store that accepted it."""
        ...

    async def remember_batch(self, writes: Sequence[MemoryWrite]) -> list:
        """Store N memories in one round trip; results parallel ``writes``."""
        ...

    async def recall(self, query: str, k: int, tenant_id: str) -> list:
        """Recall top-``k`` memories for one query, ranked by score."""
        ...

    async def recall_batch(self, queries: Sequence[RecallRequest]) -> list:
        """Run N recalls in one round trip; results parallel ``queries``."""
        ...

    async def forget(self, coord: str, tenant_id: str) -> bool:
        """Delete one memory by canonical coordinate."""
        ...

    def stream_context(
        self, query: str, k: int, tenant_id: str
    ) -> AsyncIterator:
        """Server-stream context events as each layer answers."""
        ...

    async def health(self) -> bool:
        """True when the brain answers its health RPC."""
        ...

    async def aclose(self) -> None:
        """Release pooled connections. Idempotent."""
        ...


def remember_request(write: MemoryWrite) -> RememberRequest:
    """Wrap a seam ``MemoryWrite`` in its RPC request."""
    return RememberRequest(write=write)


def remember_batch_request(writes: Sequence[MemoryWrite]) -> RememberBatchRequest:
    """Wrap N seam writes in one batch request."""
    return RememberBatchRequest(writes=list(writes))


def recall_request(query: str, k: int, tenant_id: str) -> RecallRequest:
    """Build a single recall request."""
    return RecallRequest(query=query, k=int(k), tenant_id=str(tenant_id))


def recall_batch_request(
    queries: Sequence[tuple[str, int, str]],
) -> RecallBatchRequest:
    """Build a batch recall from ``(query, k, tenant_id)`` triples.

    This is the shape that collapses N sequential round trips into one. Callers
    that today loop ``recall()`` should reach for this instead; on a LAN the
    difference for 8 recalls is roughly 160 ms down to 20 ms before the binding
    is even chosen.
    """
    return RecallBatchRequest(
        queries=[recall_request(q, k, t) for (q, k, t) in queries]
    )


def forget_request(coord: str, tenant_id: str) -> ForgetRequest:
    """Build a forget request."""
    return ForgetRequest(coord=str(coord), tenant_id=str(tenant_id))


def stream_context_request(query: str, k: int, tenant_id: str) -> StreamContextRequest:
    """Build a streaming context request."""
    return StreamContextRequest(query=query, k=int(k), tenant_id=str(tenant_id))


def health_request() -> HealthRequest:
    """Build a health request."""
    return HealthRequest()
