
"""
Django settings for somabrain project.

Aggregated from modular settings files.
"""

from somabrain.settings.django_core import *
from somabrain.settings.infra import *
from somabrain.settings.cognitive import *
from somabrain.settings.neuro import *

# Load environment-specific overrides if they exist
# from somabrain.settings.production import *  # Example: handled via env vars mostly, but good for structured overrides
