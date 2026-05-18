"""Root app migration cleanup for the split AAAS architecture.

Historically the monolithic ``somabrain`` app briefly carried AAAS models before
they were moved into the dedicated ``somabrain.aaas`` app. The current repo
keeps both migration histories, so replaying the old monolithic migration on a
fresh database tries to create AAAS tables such as ``aaas_api_keys`` twice.

For current installs, the root app only still owns ``DynamicConfig`` here. The
AAAS schema is created exclusively by ``somabrain.aaas`` migrations.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Create only the root-owned DynamicConfig table.

    Keeping the migration number preserves compatibility for existing databases,
    while removing duplicate AAAS table creation keeps fresh test databases
    aligned with the present split-app layout.
    """

    dependencies = [
        ("somabrain", "0003_oakoption"),
    ]

    operations = [
        migrations.CreateModel(
            name="DynamicConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        help_text="Config key (e.g. 'circuit_breaker.threshold')",
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "value",
                    models.JSONField(help_text="Configuration value (JSON typed)"),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Documentation for this setting",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Dynamic Configuration",
                "verbose_name_plural": "Dynamic Configurations",
            },
        ),
    ]
