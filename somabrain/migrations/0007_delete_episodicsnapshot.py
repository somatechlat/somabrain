"""Delete dead EpisodicSnapshot schema (D9).

Implement-or-delete: the model + admin + table had zero writers and zero
readers outside the admin registration. Keeping a dead schema is a ghost.

Generated for D9 (episodic_snapshots).
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Delete the unused episodic_snapshots table."""

    dependencies = [
        ("somabrain", "0006_outbox_claim_expires_at"),
    ]

    operations = [
        migrations.DeleteModel(
            name="EpisodicSnapshot",
        ),
    ]
