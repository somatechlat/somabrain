from __future__ import annotations

"""Feedback data model used in tests.

The production code may have a richer implementation, but for the unit
tests we only need a lightweight container that provides an ``event`` name
and a numeric ``score``.  Implement ``__float__`` so a ``Feedback`` instance
can be used wherever a float utility value is expected.
"""



class Feedback:
    """Simple feedback container.

    Attributes
    ----------
    event: str
        Identifier of the feedback event.
    score: float
        Numeric score representing utility or reward.
    """

def __init__(self, event: str, score: float):
        self.event = event
        self.score = float(score)

def __float__(self) -> float:
        """Allow ``float(feedback)`` to return the score."""
        return self.score
