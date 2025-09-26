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
    "sphinx.ext.autosummary",
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
    "qdrant_client",
    "redis",
    "torch",
    "transformers",
    "scipy",
    "numpy",
    "sklearn",
    "faiss",
    "pydantic_core",
    "pydantic",
    "pydantic.typing",
    # Mock internal modules that execute runtime-only code on import
    "somabrain.app",
    "somabrain.metrics",
    "somabrain.schemas",
    # Mock API routers and other runtime modules that autosummary tries to import
    "somabrain.api",
    "somabrain.api.routers",
    "somabrain.api.routers.link",
    "somabrain.api.routers.persona",
    "somabrain.api.routers.rag",
    "somabrain.thalamus",
    # defensive: mock top-level runtime modules used by the package
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

# Prefer local documentation stubs to avoid importing heavy runtime modules.
# Compute project paths first so we can remove them from sys.path if Sphinx
# already added them. This avoids a situation where the real package is
# importable before the stubs are in place.

# Ensure project paths are available so autosummary can import the real
# package and generate API pages from runtime objects. Place the project
# paths at the front of sys.path so the real code is imported instead of the
# lightweight stubs. If you want to force the stubs to be used, remove these
# entries or adjust their ordering.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
somabrain_path = os.path.join(project_root, "somabrain")

# Prepend project paths so the real package is importable during docs builds.
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if somabrain_path not in sys.path:
    sys.path.insert(1, somabrain_path)

# Also ensure the stubs path exists (kept for reference and to support mixed
# builds), but place it after the real project so it doesn't shadow imports.
_stubs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_stubs"))
if _stubs_path not in sys.path:
    sys.path.insert(2, _stubs_path)

# Provide short-name aliases for modules that sometimes appear unqualified in
# docstrings or autosummary directives (e.g. 'thalamus' instead of
# 'somabrain.thalamus'). This helps autosummary.import_by_name locate the
# correct module without requiring all docstrings to use fully-qualified names.
try:
    import importlib

    for short, full in (("thalamus", "somabrain.thalamus"), ("app", "somabrain.app")):
        try:
            mod = importlib.import_module(full)
            if short not in sys.modules:
                sys.modules[short] = mod
        except Exception:
            # If importing the real module fails, leave it alone; autodoc_mock_imports
            # will handle heavy imports.
            pass
except Exception:
    pass

# Ensure the lightweight stubs are actually used by Python's import system.
# Remove any previously-loaded somabrain modules (they may reference the
# real package) and import the stub modules from docs/_stubs. This is a
# defensive, best-effort step to avoid autosummary triggering heavy imports.
try:
    for _m in ("somabrain", "somabrain.app", "somabrain.thalamus"):
        if _m in sys.modules:
            del sys.modules[_m]
except Exception:
    # Best-effort; allow the build to continue. autodoc_mock_imports will
    # still mock heavy imports if necessary.
    pass

# With autosummary enabled we purposefully keep the real project paths on
# sys.path so Sphinx and autosummary import the real modules. If this causes
# issues in CI you can revert to the previous opt-in behavior.

# -- Options for HTML output -------------------------------------------------
# (project root and package paths are already arranged above; do not re-add
# them here to avoid making the real package win over the docs/_stubs.)

# -- Options for HTML output -------------------------------------------------
html_theme = "alabaster"
html_static_path = ["_static"]
