"""
Nano profile configuration for SomaBrain agent kernel.
Defines default dimensions, types, quotas, and deterministic settings for minimal deployments.
"""

HRR_DIM = 8192  # Global HRR dimensionality (production canonical default)
HRR_DTYPE = "float32"  # Global HRR dtype (must match everywhere)
HRR_RENORM = True  # Always unit-norm after every op
HRR_VECTOR_FAMILY = "gaussian"  # All base vectors are Gaussian, then unit-norm
# Updated global FFT epsilon documented as conservative default; per-dtype
# runtime clamps will still apply where needed.
HRR_FFT_EPSILON = 1e-6  # Small epsilon for FFT numerical stability (float32 path)
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
