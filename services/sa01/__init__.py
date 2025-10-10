"""SomaAgent01 gRPC service entrypoint.

The conversational core is implemented as a high-throughput gRPC façade that
leverages the existing SomaBrain memory service.  Downstream deployers call
``create_server`` (optionally overriding the listen port) and start the returned
``grpc.Server`` instance as part of their process supervisor.
"""

from __future__ import annotations

from typing import Optional, Tuple

import grpc

from somabrain.grpc_server import create_server as _create_memory_server

DEFAULT_PORT = 50051


def create_server(
    *,
    port: Optional[int] = None,
    max_workers: int = 16,
) -> Tuple[grpc.Server, int]:
    """Return a configured gRPC server ready to serve SomaAgent01 traffic.

    The implementation reuses the canonical memory gRPC servicer so that the
    conversational core shares a single source of truth for persistence while
    still exposing an agent-specific port (default ``50051``).  The caller is
    responsible for starting/stopping the returned server.
    """

    listen_port = port if port is not None else DEFAULT_PORT
    server, resolved = _create_memory_server(port=listen_port, max_workers=max_workers)
    return server, resolved


def serve(
    *,
    port: Optional[int] = None,
    max_workers: int = 16,
) -> None:
    """Start the SomaAgent01 gRPC server and block until termination."""

    server, resolved_port = create_server(port=port, max_workers=max_workers)
    server.start()
    try:
        server.wait_for_termination()
    finally:
        server.stop(grace=0)


__all__ = ["create_server", "serve", "DEFAULT_PORT"]
