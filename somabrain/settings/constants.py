"""Protocol and scheme constants.

Vendor and service URLs are **settings**, never literals at a call site.
This module holds only the *scheme tokens* that appear when a URL must be
normalised (for example a bare host that arrives without ``://``). An
effective base URL is always read through
``somabrain.settings.resolve.require_url``.
"""

from __future__ import annotations

# Scheme tokens used when normalising a host into a URL. These are protocol
# constants, not deployment topology — topology lives in settings/.
HTTP_SCHEME = "http"
HTTPS_SCHEME = "https"
REDIS_SCHEME = "redis"
KAFKA_SCHEME = "kafka"

HTTP_PREFIX = f"{HTTP_SCHEME}://"
HTTPS_PREFIX = f"{HTTPS_SCHEME}://"

__all__ = [
    "HTTP_SCHEME",
    "HTTPS_SCHEME",
    "REDIS_SCHEME",
    "KAFKA_SCHEME",
    "HTTP_PREFIX",
    "HTTPS_PREFIX",
]
