from dataclasses import dataclass

@dataclass
class RetrievalWeights:
    """Minimal duplicate to avoid import-time circularity in tests."""
    alpha: float
    beta: float
    gamma: float
    tau: float
