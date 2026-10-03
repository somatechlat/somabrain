
"""Standalone settings profile.

Reuses the shared Django, infrastructure, and cognitive settings modules and
pins a single tenant identity. There is no product overlay to strip: SomaBrain
is HTTP + containers only, and ``tenant_id`` is a data-partition key.
"""

import environ  # type: ignore[import-untyped]

from .cognitive import *
from .django_core import *
from .infra import *
from .neuro import *

env = environ.Env()

# =============================================================================
# STANDALONE TENANT IDENTITY
# =============================================================================

# Pin the tenant identity so a shared environment cannot leak another
# partition's key into a standalone deployment.
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS = env.bool(
    "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS",
    default=SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS,
)
SOMABRAIN_DEFAULT_TENANT = "standalone"
SOMABRAIN_TENANT_ID = "standalone"

