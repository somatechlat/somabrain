"""
Nano profile configuration for SomaBrain agent kernel.
Defines default dimensions, types, quotas, and deterministic settings for minimal deployments.
"""

HRR_DIM = 8192  # Global HRR dimensionality (production canonical default)
HRR_DTYPE = "float32"  # Global HRR dtype (must match everywhere)
HRR_RENORM = True  # Always unit-norm after every op
HRR_VECTOR_FAMILY = "bhdc"  # Binary hypervectors with deterministic permutation binding
BHDC_SPARSITY = 0.1  # Fraction of active dimensions for role/payload vectors
SDR_BITS = 2048
SDR_DENSITY = 0.03  # ~3%
CONTEXT_BUDGET_TOKENS = 2048
MAX_SUPERPOSE = 32
DEFAULT_WM_SLOTS = 12
DEFAULT_SEED = 42  # Global seed for all HRR/quantum ops

# Quotas (example, can be loaded from config)
QUOTAS = {
    "tenant": 10000,
    "tool": 1000,
    "action": 500,
}

# Determinism
DETERMINISM = True
SEED = DEFAULT_SEED  # Use this everywhere for reproducibility
