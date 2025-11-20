#!/usr/bin/env python3
"""Verify that all required environment variables for a full‑stack SomaBrain
deployment are present and non‑empty.

The script performs three main actions:
1. Ensures a ``.env`` file exists – if it is missing the script copies the
   canonical ``config/env.example`` template.
2. Loads the :class:`common.config.settings.Settings` singleton (which reads the
   ``.env`` file) and checks every field that should have a concrete value for a
   production‑grade run.
3. Prints a concise report.  It exits with ``0`` when everything is ready and
   with ``1`` when one or more required variables are missing or empty.

Running this script before ``docker compose up`` gives you a quick “certification”
that the environment is correctly configured for the **full‑local** mode
(``SOMABRAIN_MODE=full-local``) required by the ROAMDP implementation.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------
# Ensure the repository root is on ``sys.path`` so that ``common`` can be
# imported when the script is executed from any working directory.
# ``scripts`` lives two levels below the project root, so we prepend the
# parent of the parent directory (i.e. ``..``) to ``sys.path``.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import the Settings class – the singleton ``settings`` will read the .env file.
from common.config.settings import Settings


def _load_fresh_settings() -> Settings:
    """Create a fresh Settings instance after any possible .env creation.

    ``pydantic`` caches environment values on import, so we instantiate a new
    ``Settings`` object to guarantee that newly‑written variables are taken into
    account.
    """
    return Settings()


def _ensure_env_file() -> None:
    """Guarantee that a ``.env`` file is present.

    If the file does not exist we copy the example template located at
    ``config/env.example``.  The example contains safe defaults for development
    but leaves secrets (JWT, passwords, etc.) empty – the user must fill them in.
    """
    env_path = Path(".env")
    if env_path.is_file():
        return

    example_path = Path("config/env.example")
    if not example_path.is_file():
        print("❌ Neither .env nor config/env.example found.", file=sys.stderr)
        sys.exit(1)

    env_path.write_text(example_path.read_text())
    print("⚙️  Created .env from config/env.example – please edit it with real values.")


def _collect_missing(settings_obj: Settings) -> list[str]:
    """Return a list of field names that are considered missing.

    A field is *missing* when its value is ``None`` or an empty/blank string.
    Some fields (JWT secret/key, optional memory token) are allowed to be empty
    because they can be disabled in dev; they are excluded from the missing list.
    """
    missing: list[str] = []

    # Core services that must have concrete endpoints / credentials.
    required_core = [
        "postgres_dsn",
        "redis_url",
        "kafka_bootstrap_servers",
        "memory_http_endpoint",
        "jwt_secret",
        "jwt_public_key_path",
        "opa_url",
    ]

    for name in required_core:
        value = getattr(settings_obj, name, None)
        if not value:
            missing.append(name)

    # Any other string field that is empty is suspicious; we report it unless it
    # is explicitly optional (e.g., memory token).
    optional_empty = {"memory_http_token", "jwt_secret", "jwt_public_key_path"}
    # Pydantic v2 renamed ``__fields__`` to ``model_fields``.  Fall back to the
    # older attribute for compatibility with any pinned v1 installations.
    field_dict = getattr(settings_obj, "model_fields", getattr(settings_obj, "__fields__", {}))
    for field_name, model_field in field_dict.items():
        val = getattr(settings_obj, field_name)
        if isinstance(val, str) and not val.strip():
            if field_name in optional_empty:
                continue
            # Avoid duplicate entries for fields already in required_core.
            if field_name not in required_core:
                missing.append(field_name)

    return sorted(set(missing))


def main() -> int:
    _ensure_env_file()
    fresh = _load_fresh_settings()
    missing = _collect_missing(fresh)

    if missing:
        print("❌ Missing or empty required configuration values:")
        for name in missing:
            print(f"  - {name.upper()}")
        print('\nEdit the .env file and provide real values for the above entries.')
        return 1

    print("✅ All required environment variables are set and non‑empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
