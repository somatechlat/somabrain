from __future__ import annotations
import logging
from logging import Logger
from common.config.settings import settings
from common.logging import logger

"""Centralised logger for the SomaBrain codebase.

The logger is configured from :pydata:`common.config.settings` so that the
log level can be overridden via environment variables (VIBE *Integrate*).
All modules should import ``logger`` from this file rather than configuring
their own ``logging`` instance.
"""



# Import the shared settings object directly from the modern configuration package.

# Map the textual log level from Settings to the corresponding ``logging`` constant.
_LEVEL = getattr(logging, settings.log_level.upper(), logging.INFO)

logging.basicConfig(
    level=_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%m %H:%M:%S", )

# Export a module‑level logger that can be imported everywhere.
logger: Logger = logging.getLogger("somabrain")
