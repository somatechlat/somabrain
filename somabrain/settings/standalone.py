# ruff: noqa: F403,F405

"""Standalone settings profile with AAAS features stripped at import time.

The standalone runtime still reuses the shared Django, infrastructure, and
cognitive settings modules, but it forces a single-tenant view of the world by
removing AAAS apps/middleware and pinning the default tenant identity.
"""

import environ  # type: ignore[import-untyped]

from .django_core import *
from .infra import *
from .cognitive import *
from .neuro import *

env = environ.Env()

# =============================================================================
# STANDALONE ISOLATION - STRIP AAAS
# =============================================================================

# Keep AAAS Application in standalone so auth migrations and API keys work.
# Only the AAAS middleware (billing, rate limiting) is removed.

# Remove AAAS Middleware (Billing, Rate Limiting, etc)
MIDDLEWARE = [
    m
    for m in MIDDLEWARE
    if "somabrain.aaas" not in m and "UsageTrackingMiddleware" not in m
]

# Force standalone tenant identity even if the outer shell inherited AAAS-ish
# variables from another environment.
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS = env.bool(
    "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS",
    default=SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS,
)
SOMABRAIN_DEFAULT_TENANT = "standalone"
SOMABRAIN_TENANT_ID = "standalone"

print(f"Loaded STANDALONE settings. Apps: {len(INSTALLED_APPS)}")
