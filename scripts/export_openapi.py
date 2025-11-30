#!/usr/bin/env python3
"""Export OpenAPI specification to artifacts/openapi.json."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

from somabrain.app import app

out_dir = Path("artifacts")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "openapi.json"

openapi_schema = get_openapi(
    title="SomaBrain API",
    version="1.0.0",
    description="SomaBrain context and feedback endpoints",
    routes=app.routes, )

out_path.write_text(json.dumps(openapi_schema, indent=2))
print(f"OpenAPI schema written to {out_path}")
