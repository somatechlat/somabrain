"""Legacy hybrid quantum layer placeholder.

The FFT-based hybrid quantum implementation has been fully removed. Importing
this module now raises immediately to surface stale dependencies.
"""

raise ImportError(
    "somabrain.quantum_hybrid has been removed; use somabrain.quantum.QuantumLayer instead"
)
