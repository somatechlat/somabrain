from __future__ import annotations
from dataclasses import dataclass

"""Stub implementation of the cut‑over controller.

The test suite imports ``CutoverController`` and ``CutoverError`` from this
module.  The real controller coordinates graceful transitions between
configuration versions.  For testing we provide a minimal in‑memory version that
stores a ``state`` attribute and raises ``CutoverError`` for illegal actions.
"""




class CutoverError(RuntimeError):
    """Raised when an invalid cut‑over operation is attempted."""


@dataclass
class CutoverController:
    """Very small stub used by tests.

    Attributes
    ----------
    state: str
        Current state of the controller – defaults to ``"idle"``.
    """

    state: str = "idle"

def start(self) -> None:
        if self.state != "idle":
            raise CutoverError("Controller already started")
        self.state = "running"

def stop(self) -> None:
        if self.state != "running":
            raise CutoverError("Controller not running")
        self.state = "stopped"
