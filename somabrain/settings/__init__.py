"""Environment-based settings loader."""

import os
from pathlib import Path

# Load .env file before importing any settings
from dotenv import load_dotenv

# somabrain/settings/__init__.py -> somabrain/settings -> somabrain -> PROJECT_ROOT
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

ENVIRONMENT = os.environ.get("DJANGO_ENV", "development")

if ENVIRONMENT == "production":
    from .production import *  # noqa
elif ENVIRONMENT == "staging":
    from .staging import *  # noqa
else:
    from .development import *  # noqa

__all__ = ["ENVIRONMENT"]