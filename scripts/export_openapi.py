#!/usr/bin/env python3
"""Export OpenAPI specification to artifacts/openapi.json using Django Ninja.

This script exports the OpenAPI schema from the Django Ninja API.
It uses Django's setup mechanics to properly initialize the application.
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

# Setup Django before importing app modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")

import django
django.setup()

from somabrain.api import api  # Django Ninja API instance

out_dir = Path("artifacts")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "openapi.json"

# Django Ninja provides OpenAPI schema via api.get_openapi_schema()
openapi_schema = api.get_openapi_schema()

out_path.write_text(json.dumps(openapi_schema, indent=2))
print(f"OpenAPI schema written to {out_path}")