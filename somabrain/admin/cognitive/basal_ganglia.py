"""Basal ganglia action selection.

Real mechanism (see SOMA-BR-MATH-TRUTH-001 T80): Boltzmann (softmax)
selection over action values with ε-exploration. The basal ganglia is the
final decision stage that turns competing action values into one selected
action. It is not an identity of caller-supplied boolean gates.

Math:
    p(a) = exp((v_a − v_max) / T) / Σ_b exp((v_b − v_max) / T)

    With probability ε the policy explores: the action is drawn uniformly
    from the candidate set. Otherwise the action is sampled from p
    (argmax when T ≤ 0). T must be > 0 for the stochastic path.

Wired into ``POST /cognitive/act`` via ``eval_step``: candidate action
values are derived from salience and the amygdala gates, one action is
selected, and the selection determines the step's store/act flags and
``policy`` payload.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActionSelection:
    """Outcome of one basal-ganglia action-selection step.

    Attributes
    ----------
    action:
        Name of the selected action.
    probs:
        Softmax probability of every candidate (after ε-exploration draw
        these are still the Boltzmann probabilities; ``explored`` records
        whether the uniform exploration branch was taken).
    values:
        The action values that were fed to the selector.
    explored:
        True when the uniform ε-exploration branch chose the action.
    temperature:
        Temperature T used for the softmax.
    """

    action: str
    probs: dict[str, float] = field(default_factory=dict)
    values: dict[str, float] = field(default_factory=dict)
    explored: bool = False
    temperature: float = 1.0

    def as_dict(self) -> dict[str, object]:
        """JSON-serialisable view for the /act ``policy`` field."""
        return {
            "action": self.action,
            "probs": dict(self.probs),
            "values": dict(self.values),
            "explored": self.explored,
            "temperature": float(self.temperature),
        }


@dataclass
class PolicyDecision:
    """Store/act flags implied by a selected action name.

    Attributes
    ----------
    store : bool
        Whether to store the memory.
    act : bool
        Whether to act on the memory.
    action : str
        The selected action name that produced these flags.
    """

    store: bool
    act: bool
    action: str = "skip"


#: Action names whose selection opens the store / act flags.
STORE_ACTIONS: frozenset[str] = frozenset({"store", "both"})
ACT_ACTIONS: frozenset[str] = frozenset({"act", "both"})


class BasalGangliaPolicy:
    """Boltzmann action selection with ε-exploration.

    Parameters
    ----------
    temperature:
        Default softmax temperature T (> 0). Lower T sharpens selection
        toward the greedy action; higher T flattens it.
    epsilon:
        Default exploration rate ε ∈ [0, 1]. With probability ε the action
        is drawn uniformly from the candidate set.
    seed:
        Optional RNG seed for deterministic selection in tests.
    """

    def __init__(
        self,
        temperature: float = 1.0,
        epsilon: float = 0.0,
        seed: int | None = None,
    ) -> None:
        self.temperature = self._check_temperature(temperature)
        self.epsilon = self._check_epsilon(epsilon)
        self._rng = random.Random(seed)

    @staticmethod
    def _check_temperature(temperature: float) -> float:
        t = float(temperature)
        if not math.isfinite(t) or t <= 0.0:
            raise ValueError("temperature must be finite and > 0")
        return t

    @staticmethod
    def _check_epsilon(epsilon: float) -> float:
        e = float(epsilon)
        if not math.isfinite(e) or not (0.0 <= e <= 1.0):
            raise ValueError("epsilon must be in [0, 1]")
        return e

    @staticmethod
    def softmax_probs(values: Mapping[str, float], temperature: float) -> dict[str, float]:
        """Max-shifted Boltzmann probabilities p(a) ∝ exp((v_a − v_max) / T)."""
        if not values:
            raise ValueError("values must be non-empty")
        t = BasalGangliaPolicy._check_temperature(temperature)
        items = [(str(k), float(v)) for k, v in values.items()]
        for name, v in items:
            if not math.isfinite(v):
                raise ValueError(f"action value for {name!r} must be finite")
        v_max = max(v for _, v in items)
        exps = {name: math.exp((v - v_max) / t) for name, v in items}
        total = sum(exps.values())
        if total <= 0.0 or not math.isfinite(total):
            # Degenerate (all underflow): uniform
            n = len(items)
            return {name: 1.0 / n for name, _ in items}
        return {name: e / total for name, e in exps.items()}

    def select(
        self,
        values: Mapping[str, float],
        *,
        temperature: float | None = None,
        epsilon: float | None = None,
        rng: random.Random | None = None,
    ) -> ActionSelection:
        """Select one action from ``values`` via Boltzmann softmax + ε-exploration.

        Parameters
        ----------
        values:
            Mapping of action name → utility. Must be non-empty with finite
            values. Two candidates with different utilities yield a non-trivial
            (non-pass-through) selection: the higher utility is chosen more
            often, with residual probability on the other under T > 0 and/or
            ε > 0.
        temperature:
            Optional override of the instance default T.
        epsilon:
            Optional override of the instance default ε.
        rng:
            Optional ``random.Random`` (for tests). Defaults to the instance RNG.
        """
        t = self._check_temperature(
            self.temperature if temperature is None else temperature
        )
        eps = self._check_epsilon(self.epsilon if epsilon is None else epsilon)
        source = rng if rng is not None else self._rng

        probs = self.softmax_probs(values, t)
        names = list(probs.keys())
        explored = False
        if eps > 0.0 and source.random() < eps:
            action = source.choice(names)
            explored = True
        else:
            # Inverse-CDF sample from the Boltzmann distribution.
            r = source.random()
            acc = 0.0
            action = names[-1]
            for name in names:
                acc += probs[name]
                if r <= acc:
                    action = name
                    break

        return ActionSelection(
            action=action,
            probs=probs,
            values={str(k): float(v) for k, v in values.items()},
            explored=explored,
            temperature=t,
        )

    def decide(
        self,
        values: Mapping[str, float],
        *,
        temperature: float | None = None,
        epsilon: float | None = None,
        rng: random.Random | None = None,
    ) -> tuple[PolicyDecision, ActionSelection]:
        """Select an action and map it to store/act flags.

        ``store`` is true for actions in ``STORE_ACTIONS`` (``store``, ``both``);
        ``act`` is true for actions in ``ACT_ACTIONS`` (``act``, ``both``).
        """
        selection = self.select(
            values, temperature=temperature, epsilon=epsilon, rng=rng
        )
        decision = PolicyDecision(
            store=selection.action in STORE_ACTIONS,
            act=selection.action in ACT_ACTIONS,
            action=selection.action,
        )
        return decision, selection
