"""Minimal type stubs for the ``etcd3`` package used in the project.

Only the symbols accessed by the codebase are defined.  This is sufficient for
static analysis (Pyright) without pulling the heavy runtime dependency.
"""

from typing import Any, Callable, Optional

class _Event:
    key: bytes
    value: Optional[bytes]

def client(*, host: str = ..., port: int = ..., timeout: float = ...) -> "_Client": ...

class _Client:
    def get(self, key: str) -> tuple[Optional[bytes], Any]: ...
    def put(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def add_watch_prefix_callback(
        self, prefix: str, callback: Callable[[_Event], Any]
    ) -> int: ...
    def cancel_watch(self, watch_id: int) -> None: ...
