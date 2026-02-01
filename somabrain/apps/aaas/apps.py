"""
Django App Configuration for AAAS module.
"""

from django.apps import AppConfig


class AaasConfig(AppConfig):
    """Configuration for the AAAS application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "somabrain.apps.aaas"
    verbose_name = "SomaBrain AAAS"

    def ready(self):
        """Run on app ready - import signals if needed."""
        pass
