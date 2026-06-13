"""Module wsgi."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")

# Apply Vault/bootstrap secrets and infrastructure-specific env mutations once
# before Django imports the settings modules.
from somabrain.settings.django_core import configure_vault_secrets
from somabrain.settings.infra import configure_infra_secrets, configure_tf_metal

configure_vault_secrets()
configure_tf_metal()
configure_infra_secrets()

application = get_wsgi_application()
