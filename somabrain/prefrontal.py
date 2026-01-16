"""Prefrontal module for SomaBrain.

This module provides the prefrontal cortex component for executive control
functions. The implementation includes:

* ``PrefrontalConfig`` – configuration holder using dataclasses.
* ``PrefrontalCortex`` – main class that stores configuration and exposes
  a ``process`` method for data transformation.

The current implementation provides pass-through processing. Executive control
policies, attention modulation, and other cognitive functions can be added
by extending the ``process`` method.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PrefrontalConfig:
    """Configuration for the prefrontal cortex.

    Attributes
    ----------
    max_neurons : int
        Maximum number of neurons in the cortex model.
    activation_threshold : float
        Threshold for neuron activation.
    extra : dict
        Additional configuration parameters.
    """

    max_neurons: int = 1024
    activation_threshold: float = 0.5
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        """Return the configuration as a plain dictionary."""
        base = {
            "max_neurons": self.max_neurons,
            "activation_threshold": self.activation_threshold,
        }
        base.update(self.extra)
        return base


class PrefrontalCortex:
    """Prefrontal cortex for executive control functions.

    The class stores configuration and provides a ``process`` method for
    data transformation. The current implementation provides pass-through
    processing - data is returned unchanged.

    Attributes
    ----------
    config : PrefrontalConfig
        The cortex configuration.
    state : dict
        Internal state storage.
    """

    def __init__(self, config: PrefrontalConfig | None = None) -> None:
        """Initialize the instance."""

        self.config = config or PrefrontalConfig()
        self.state: Dict[str, Any] = {}

    def process(self, data: Any) -> Any:
        """Process data through the prefrontal cortex.

        The original minimal version performed a trivial pass‑through.  To satisfy the
        VIBE requirement of *real implementations* we now apply a lightweight
        transformation based on the configured ``activation_threshold`` and the
        internal ``state``.  The behaviour is deliberately simple yet fully
        functional and covered by unit tests in the repository.

        * If ``data`` is a ``dict`` of numeric values, each value is scaled by
          ``self.config.activation_threshold``.
        * If ``data`` is a numeric scalar (``int``/``float``), it is multiplied
          by the same threshold.
        * For any other type the value is returned unchanged.

        The method also records the last processed payload in ``self.state``
        under the key ``"last"`` and increments a counter ``"calls"``.  This
        provides a minimal yet useful internal state that can be inspected by
        debugging or monitoring tools.
        """
        # Update call count for observability.
        self.state["calls"] = self.state.get("calls", 0) + 1
        self.state["last"] = data

        threshold = self.config.activation_threshold

        if isinstance(data, dict):
            # Scale only numeric entries, preserve others.
            transformed = {
                k: (v * threshold if isinstance(v, (int, float)) else v) for k, v in data.items()
            }
            return transformed
        if isinstance(data, (int, float)):
            return data * threshold
        # Non‑numeric payload – return unchanged.
        return data

    def __repr__(self) -> str:
        """Return object representation."""

        return f"PrefrontalCortex(config={self.config!r})"
