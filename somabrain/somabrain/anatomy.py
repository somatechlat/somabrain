from __future__ import annotations

"""
Anatomy-aligned aliases for SomaBrain components.

These thin wrappers/aliases let external code import brain-inspired names
without changing internal implementations. They keep the architecture
readable and biologically grounded, while preserving backwards compatibility.
"""

from .wm import WorkingMemory as _WorkingMemory
from .prediction import StubPredictor as _StubPredictor
from .memory_client import MemoryClient as _MemoryClient
from .thalamus import ThalamusRouter as ThalamusRouter
from .amygdala import AmygdalaSalience as AmygdalaSalience
from .basal_ganglia import BasalGangliaPolicy as BasalGangliaPolicy
from .neuromodulators import Neuromodulators as Neuromodulators
from .quantum import QuantumLayer as QuantumLayer, HRRConfig as HRRConfig


class PrefrontalWM(_WorkingMemory):
    """Prefrontal Cortex — Working Memory buffer.

    Alias of WorkingMemory; encapsulates short-term context and similarity-based recall.
    """

    pass


class CerebellumPredictor(_StubPredictor):
    """Cerebellum — predictor + error signal.

    Alias of StubPredictor for now; pluggable with LLM/ML providers later.
    """

    pass


class HippocampusEpisodic(_MemoryClient):
    """Hippocampus — episodic memory coordinator.

    Thin alias over MemoryClient; handles storing and recalling events.
    """

    pass


class CortexSemantic(_MemoryClient):
    """Cortex — semantic memory store.

    Thin alias over MemoryClient; used for distilled facts/summaries.
    """

    pass

