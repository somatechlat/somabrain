"""Initial migration for brain_settings table."""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('somabrain', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrainSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(db_index=True, max_length=255)),
                ('tenant', models.CharField(db_index=True, default='default', max_length=100)),
                ('value_float', models.FloatField(blank=True, null=True)),
                ('value_int', models.IntegerField(blank=True, null=True)),
                ('value_bool', models.BooleanField(blank=True, null=True)),
                ('value_type', models.CharField(default='float', max_length=20)),
                ('category', models.CharField(db_index=True, default='brain', max_length=100)),
                ('is_learnable', models.BooleanField(default=False)),
                ('min_value', models.FloatField(blank=True, null=True)),
                ('max_value', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'brain_settings',
                'unique_together': {('key', 'tenant')},
            },
        ),
    ]
