"""Learning math surface — re-exports the canonical somabrain.math implementations.

Single source of truth (VIBE): cosine similarity and Frequent-Directions live
in ``somabrain.math``. This module is the learning package's import surface.
"""

from somabrain.math.fd_rho import FrequentDirections
from somabrain.math.similarity import cosine_similarity

__all__ = ["FrequentDirections", "cosine_similarity"]
