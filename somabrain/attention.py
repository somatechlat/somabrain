"""
Attention Module with Bandit-based Source Selection.

Implements a simple UCB1 multi-armed bandit for selecting context sources
(e.g., WM, LTM, HRR, SDR). Lightweight and dependency-free.

Contracts:
- UCB1Bandit.add_arm(name)
- UCB1Bandit.select() -> str (arm name)
- UCB1Bandit.update(name, reward: float)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Arm:
    """Arm class implementation."""

    name: str
    count: int = 0
    value: float = 0.0  # running mean reward


class UCB1Bandit:
    """Ucb1bandit class implementation."""

    def __init__(self):
        """Initialize the instance."""

        self._arms: Dict[str, Arm] = {}
        self._n: int = 0

    def add_arm(self, name: str) -> None:
        """Execute add arm.

            Args:
                name: The name.
            """

        if name not in self._arms:
            self._arms[name] = Arm(name)

    def select(self) -> Optional[str]:
        """Execute select.
            """

        if not self._arms:
            return None
        # Ensure all arms are tried at least once
        for arm in self._arms.values():
            if arm.count == 0:
                return arm.name
        # UCB1 selection
        self._n = max(self._n, 1)
        best_name = None
        best_score = -1e9
        for arm in self._arms.values():
            ucb = arm.value + math.sqrt(2.0 * math.log(self._n) / arm.count)
            if ucb > best_score:
                best_score = ucb
                best_name = arm.name
        return best_name

    def update(self, name: str, reward: float) -> None:
        """Execute update.

            Args:
                name: The name.
                reward: The reward.
            """

        arm = self._arms.get(name)
        if arm is None:
            return
        arm.count += 1
        self._n += 1
        # incremental mean
        arm.value += (float(reward) - arm.value) / arm.count