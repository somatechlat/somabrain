"""
SomaBrain App Configuration.

VIBE COMPLIANT: Explicit initialization of runtime singletons.
"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SomaBrainConfig(AppConfig):
    """
    Django AppConfig for the main SomaBrain application.

    Handles initialization of cognitive singletons (Memory, Embedder)
    when the application starts.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "somabrain"
    verbose_name = "SomaBrain Cognitive Core"

    def ready(self):
        """Keep Django app startup side-effect free.

        Runtime singletons are initialized either by the standalone entrypoint
        or lazily by the runtime manager. Doing that work here blocks
        ``django.setup()`` for management commands and startup probes.
        """
        logger.info("SomaBrain AppConfig ready; runtime initialization is deferred.")
