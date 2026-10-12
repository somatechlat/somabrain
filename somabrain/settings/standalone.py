"""Standalone settings profile.

Reuses the shared Django, infrastructure, and cognitive settings modules and
pins a single tenant identity. There is no product overlay to strip: SomaBrain
is HTTP + containers only, and ``tenant_id`` is a data-partition key.
"""

import environ  # type: ignore[import-untyped]

from .cognitive import *  # noqa: F403,F405  (Django settings composition)
from .django_core import *  # noqa: F403,F405  (Django settings composition)
from .infra import *  # noqa: F403,F405  (Django settings composition)
from .neuro import *  # noqa: F403,F405  (Django settings composition)

env = environ.Env()

# =============================================================================
# STANDALONE TENANT IDENTITY
# =============================================================================

# Pin the tenant identity so a shared environment cannot leak another
# partition's key into a standalone deployment.
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS = env.bool(
    "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS",
    default=globals().get("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", False),  # noqa: F405
)
SOMABRAIN_DEFAULT_TENANT = "standalone"
SOMABRAIN_TENANT_ID = "standalone"
