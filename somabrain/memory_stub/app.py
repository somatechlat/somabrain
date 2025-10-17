"""Unsupported memory stub.

This module remains solely to avoid import errors in legacy tooling. The
project requires a real HTTP memory service; attempting to use this module will
raise immediately so that no in-process mock is ever relied upon.
"""

from __future__ import annotations

import typing as _t


def __getattr__(name: str) -> _t.Any:  # pragma: no cover - defensive guard
    raise RuntimeError(
        "somabrain.memory_stub is disabled. Provision an external memory service "
        "and set SOMABRAIN_MEMORY_HTTP_ENDPOINT accordingly."
    )


class DisabledMemoryStub:
    def __init__(self, *args: object, **kwargs: object) -> None:  # pragma: no cover
        raise RuntimeError(
            "Memory stub disabled. Point SOMABRAIN_MEMORY_HTTP_ENDPOINT at the "
            "real memory service."
        )


app = DisabledMemoryStub  # type: ignore
