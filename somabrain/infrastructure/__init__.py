"""Infrastructure package for SomaBrain.

This package contains shared infrastructure components used across the system.
"""

import os
from typing import Optional


def get_redis_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Redis connection URL from environment or shared settings."""
    url = os.getenv("SOMABRAIN_REDIS_URL")
    if url:
        return url
    url = os.getenv("REDIS_URL")
    if url:
        return url
    return default