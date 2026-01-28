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
        """
        Initialize runtime singletons when Django is ready.

        This ensures that:
        1. Settings are loaded
        2. Models are ready (if needed)
        3. Singletons are initialized exactly once per process
        """
        from somabrain.runtime import initialize_runtime

        logger.info("⚡ SomaBrain AppConfig: Initializing runtime singletons...")
        try:
            status = initialize_runtime()
            logger.info(f"✅ SomaBrain Runtime initialized: {status}")
        except Exception as e:
            logger.error(f"❌ SomaBrain Runtime initialization FAILED: {e}")
            # We don't raise here to allow Django to start, but API endpoints will fail 503
            # which is the correct behavior (Liveness probe vs Readiness probe)
