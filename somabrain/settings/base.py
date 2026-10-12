"""
Django settings for somabrain project.

Aggregated from modular settings files.
"""

from somabrain.settings.cognitive import *  # noqa: F403,F405  (Django settings composition)
from somabrain.settings.django_core import *  # noqa: F403,F405  (Django settings composition)
from somabrain.settings.infra import *  # noqa: F403,F405  (Django settings composition)
from somabrain.settings.neuro import *  # noqa: F403,F405  (Django settings composition)

# Load environment-specific overrides if they exist
# from somabrain.settings.production import *  # Example: handled via env vars mostly, but good for structured overrides  # noqa: F403,F405  (Django settings composition)
