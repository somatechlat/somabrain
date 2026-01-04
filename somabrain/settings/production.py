"""Production settings with strict validation."""

from .base import *  # noqa
from .service_registry import SERVICES

import os

DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
ENVIRONMENT = "production"

missing_services = SERVICES.validate_required(ENVIRONMENT)
if missing_services:
    raise ValueError(
        f"SomaBrain production startup blocked:\n"
        f"{', '.join(missing_services)}\n"
        f"See .env.example for configuration"
    )
