from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Initialize default brain settings for a tenant"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            type=str,
            required=True,
            help=(
                "Tenant ID to seed. Must match SOMABRAIN_DEFAULT_TENANT — "
                "there is no silent default (T-5 / Rule 91)."
            ),
        )

    def handle(self, *args, **options):
        from somabrain.settings.resolve import require_setting, require_tenant

        tenant = options["tenant"]
        # Fail-closed: the explicit --tenant must equal the operator-chosen
        # base profile. A mismatch seeds the wrong partition and makes every
        # later read look "configured" on the wrong tenant.
        base = require_tenant(require_setting("SOMABRAIN_DEFAULT_TENANT"))
        if str(tenant).strip() != base:
            raise CommandError(
                f"--tenant {tenant!r} does not match SOMABRAIN_DEFAULT_TENANT={base!r}. "
                "Refusing to seed the wrong partition."
            )
        tenant = require_tenant(tenant)
        self.stdout.write(f"Initializing defaults for tenant: {tenant}...")
        from somabrain.brain_settings.models import BrainSetting

        created = BrainSetting.initialize_defaults(tenant=tenant)
        self.stdout.write(
            self.style.SUCCESS(f"Successfully initialized {created} settings.")
        )
