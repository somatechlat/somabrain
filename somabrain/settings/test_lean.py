from somabrain.settings.base import *

# Override INSTALLED_APPS to minimal set for SomaBrain core logic testing
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "somabrain",  # The core app we are testing
    "somabrain.brain_settings", # Explicitly add sub-app if needed? No, somabrain is the app.
]

# DISABLE MIGRATIONS for somabrain to force table creation from models
# This avoids the "aaas" dependency hell in the migration graph
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Ensure no other apps interfere
