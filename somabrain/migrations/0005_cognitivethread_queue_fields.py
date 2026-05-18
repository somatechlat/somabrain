from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("somabrain", "0004_apikey_auditlog_brainsetting_dynamicconfig_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cognitivethread",
            name="cursor",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="cognitivethread",
            name="options",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="cognitivethread",
            name="content",
            field=models.TextField(blank=True, default=""),
        ),
    ]
