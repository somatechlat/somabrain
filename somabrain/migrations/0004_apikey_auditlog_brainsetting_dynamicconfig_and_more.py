"""Root app migration — DynamicConfig only.

Historically this migration also created the product-tenancy tables (API keys,
audit log, brain settings) that were later split into a separate app. That
product overlay has since been removed from SomaBrain entirely: it is an HTTP +
containers service, and ``tenant_id`` is a data-partition key rather than a
product tenancy. Only the root-owned ``DynamicConfig`` table is created here.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Create only the root-owned DynamicConfig table.

    The migration number is preserved so existing databases keep a stable
    history; only the table set narrowed.
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
