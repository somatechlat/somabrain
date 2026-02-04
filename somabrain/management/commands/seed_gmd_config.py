from django.core.management.base import BaseCommand
from somabrain.brain_settings.models import BrainSetting

class Command(BaseCommand):
    help = "Seed Governing Memory Dynamics (GMD) parameters into BrainSetting"

    def handle(self, *args, **options):
        self.stdout.write("Initializing BrainSetting defaults...")
        count = BrainSetting.initialize_defaults()
        self.stdout.write(self.style.SUCCESS(f"Initialized {count} settings."))

        # Ensure active mode is ANALYTIC for consistent testing
        BrainSetting.set("active_brain_mode", "ANALYTIC")
        self.stdout.write(self.style.SUCCESS("Set active_brain_mode to ANALYTIC."))
