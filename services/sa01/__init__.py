"""SomaAgent01 gRPC service entrypoint.

The service implementation remains under development.  This module
exposes a ``get_server`` helper so subsequent sprints can wire the gRPC
server without refactoring import paths again.
"""

from typing import Any


def get_server(*_: Any, **__: Any) -> Any:
    """Placeholder accessor for the gRPC server.

    The implementation will be provided in the follow-up sprints.  The
    function exists so deployment manifests and CI references remain
    stable while we continue the extraction work.
    """

    raise NotImplementedError("SomaAgent01 server bootstrap not yet migrated")


__all__ = ["get_server"]
