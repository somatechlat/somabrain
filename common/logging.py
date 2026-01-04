"""Centralised logger for the SomaBrain codebase.

The logger is configured from :pydata:`common.config.settings` so that the
log level can be overridden via environment variables (VIBE *Integrate*).
All modules should import ``logger`` from this file rather than configuring
their own ``logging`` instance.
"""

from __future__ import annotations

import logging
from logging import Logger

# Import Django settings
from django.conf import settings

# Configure logging from Django settings
_LEVEL = getattr(logging, settings.SOMABRAIN_LOG_LEVEL.upper(), logging.INFO)

logging.basicConfig(
    level=_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%m %H:%M:%S",
)

# Export a module‑level logger that can be imported everywhere.
logger: Logger = logging.getLogger("somabrain")