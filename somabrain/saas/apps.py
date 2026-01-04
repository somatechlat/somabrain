"""
Django App Configuration for SaaS module.
"""

from django.apps import AppConfig


class SaasConfig(AppConfig):
    """Configuration for the SaaS application."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "somabrain.saas"
    verbose_name = "SomaBrain SaaS"
    
    def ready(self):
        """Run on app ready - import signals if needed."""
        pass