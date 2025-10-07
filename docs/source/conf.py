# Configuration file for the Sphinx documentation builder.

import os
import sys

# -- Project information -----------------------------------------------------
project = "SOMABRAIN"
copyright = "2025, SomaBrain Team"
author = "SomaBrain Team"
release = "0.1"

# -- General configuration ---------------------------------------------------
# Autosummary can import your codebase which may cause heavy runtime imports
# (pydantic/fastapi/etc). Make it opt-in: set DOCS_AUTOSUMMARY=1 in your
# environment to enable autosummary locally. CI builds should leave it unset
# so the docs build remains deterministic and side-effect free.
# Enable autosummary by default. The project uses autosummary to generate
# API reference pages automatically from the real package. This was previously
# opt-in via the DOCS_AUTOSUMMARY env var; the user requested autosummary be
# always enabled for local and CI builds.
AUTOSUMMARY_ENABLED = True

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
]

# Always generate autosummary source files so the API docs are produced.
autosummary_generate = True

# Suppress some noisy warnings coming from autodoc/autosummary during builds
# (we still try to fix doc sources where appropriate). This prevents a flood
# of warnings for optional runtime-only modules and autosummary-generated
# artifacts.
suppress_warnings = [
    "autodoc",
    "autosummary",
]

# Prevent Sphinx autodoc from failing on optional or runtime-only third-party
# imports used by the application. Internal somabrain modules are provided
# via lightweight stubs under docs/_stubs to avoid heavy imports.
autodoc_mock_imports = [
    "redis",
    "qdrant_client",
    "torch",
    "transformers",
    "fastapi",
    "starlette",
]

templates_path = ["_templates"]

# Exclude autosummary-generated stubs from the build to avoid orphan pages
# Keep autosummary-generated content included; use stubs or mocks for heavy imports.
# Exclude autosummary/generated API stubs from the top-level build.
# These are generated pages that duplicate autodoc output; we intentionally
# exclude them from the rendered site to avoid duplicate-object and orphan
# warnings. Keep `autosummary_generate=True` so the source can be regenerated
# when desired, but exclude the generated files from the published site.
exclude_patterns = [
    "generated/**",
]

# ---------------------------------------------------------------------------
# Simplified configuration – keep only what is needed for clean builds
# ---------------------------------------------------------------------------
# Project information (unchanged)
# ---------------------------------------------------------------------------
# The heavy path‑manipulation logic is removed – we simply prepend the repository
# root to ``sys.path`` so autodoc can import the real package.  Heavy third‑party
# imports are safely mocked via ``autodoc_mock_imports``.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Extensions – we keep the most useful ones only
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
]

# Autosummary – optional, disabled by default for a faster, clutter‑free build.
# Users who want API pages can enable it locally via ``AUTOSUMMARY=1``.
AUTOSUMMARY_ENABLED = os.getenv("AUTOSUMMARY") == "1"
if AUTOSUMMARY_ENABLED:
    extensions.append("sphinx.ext.autosummary")
    autosummary_generate = True
else:
    autosummary_generate = False

# Mock heavy imports – keep the list short and focused.
autodoc_mock_imports = [
    "redis",
    "qdrant_client",
    "torch",
    "transformers",
    "fastapi",
    "starlette",
]

# Templates & static paths (unchanged)
templates_path = ["_templates"]
html_static_path = ["_static"]
html_theme = "alabaster"

# Exclude patterns – keep the default simple set.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
