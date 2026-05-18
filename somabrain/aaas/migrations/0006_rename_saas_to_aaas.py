"""
Django Migration: Rename saas_* tables to aaas_*

This migration renames all database tables from the legacy 'saas_' prefix
to the new 'aaas_' (Agent-As-A-Service) prefix.

Run with: python manage.py migrate somabrain.aaas

VIBE Compliance:
- Rule 10: Django ORM only
- Rule 100: Centralized configuration
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Keep legacy rename migration as a no-op for current installs.

    The checked-in migration history already creates AAAS tables with their
    ``aaas_*`` names from the initial migrations onward. Running table renames
    here causes fresh databases to collide with already-created tables such as
    ``aaas_subscriptions``. Preserve the migration number for compatibility, but
    make its database effect explicit no-op for modern installs.
    """

    dependencies = [
        # This should be the last migration before this one
        ("aaas", "0005_notifications"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
