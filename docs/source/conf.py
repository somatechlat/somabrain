# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Project information -----------------------------------------------------
project = "SOMABRAIN"
copyright = "2025, SomaBrain Team"
author = "SomaBrain Team"
release = "0.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "myst_parser",
]
# Avoid autosummary creating many generated .rst files on every build. Set to
# False so generation is explicit (reduces clutter/noise during CI/doc builds).
autosummary_generate = False

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
    "somafractalmemory",
    "qdrant_client",
    "redis",
    "torch",
    "transformers",
    "scipy",
    "numpy",
    "sklearn",
    "faiss",
    "pydantic_core",
    # Mock internal modules that execute runtime-only code on import
    "somabrain.app",
    "somabrain.metrics",
    "somabrain.schemas",
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
    "_autosummary/**",
    "generated/**",
]

# Add the project root and somabrain package to sys.path for autodoc
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
somabrain_path = os.path.join(project_root, "somabrain")
sys.path.insert(0, project_root)
sys.path.insert(0, somabrain_path)

# Prefer local documentation stubs to avoid importing heavy runtime modules.
# Place docs/_stubs at the front of sys.path so Sphinx imports the stubs.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../_stubs"))
)


# -- Options for HTML output -------------------------------------------------
html_theme = "alabaster"
html_static_path = ["_static"]
