from django.core.management.base import BaseCommand

from somabrain.brain_settings.models import BrainSetting


class Command(BaseCommand):
    help = "Seed Governing Memory Dynamics (GMD) parameters into BrainSetting"

    def handle(self, *args, **options):
        self.stdout.write("Initializing BrainSetting defaults...")
        from somabrain.settings.resolve import require_setting
        from somabrain.brain_settings.models import _base_profile
        count = BrainSetting.initialize_defaults(_base_profile())
        self.stdout.write(self.style.SUCCESS(f"Initialized {count} settings."))

        # Ensure active mode is ANALYTIC for consistent testing
        from somabrain.settings.resolve import require_tenant

        BrainSetting.set("active_brain_mode", "ANALYTIC", require_tenant())
        self.stdout.write(self.style.SUCCESS("Set active_brain_mode to ANALYTIC."))
