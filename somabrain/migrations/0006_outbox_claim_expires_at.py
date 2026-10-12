from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("somabrain", "0005_cognitivethread_queue_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboxevent",
            name="claim_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="outboxevent",
            name="status",
            field=models.CharField(db_index=True, default="pending", max_length=50),
        ),
    ]
