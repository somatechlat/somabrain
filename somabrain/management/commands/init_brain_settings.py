from django.core.management.base import BaseCommand
from somabrain.brain_settings.models import BrainSetting

class Command(BaseCommand):
    help = "Initialize default brain settings for a tenant"

    def add_arguments(self, parser):
        parser.add_argument("--tenant", type=str, default="default", help="Tenant ID")

    def handle(self, *args, **options):
        tenant = options["tenant"]
        self.stdout.write(f"Initializing defaults for tenant: {tenant}...")
        created = BrainSetting.initialize_defaults(tenant=tenant)
        self.stdout.write(self.style.SUCCESS(f"Successfully initialized {created} settings."))
