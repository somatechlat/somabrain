# Configuration file for the Sphinx documentation builder.
# SOMA Stack Documentation - SomaBrain
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import django

# Add project root to path for autodoc
sys.path.insert(0, os.path.abspath("../.."))

import warnings

# Initialize Django for model introspection
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
try:
    django.setup()
except Exception:
    pass  # Allow doc build without full Django setup

# Suppress Django Ninja view signature warnings
warnings.filterwarnings("ignore", category=UserWarning, module="ninja")
warnings.filterwarnings("ignore", message=".*Field\\(s\\).*in the view path.*")
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated as an API.*")

# -- Project information -----------------------------------------------------
project = "SomaBrain"
copyright = "2026, SomaTech"
author = "SomaTech Engineering"
version = "1.0.0"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",  # Auto-generate docs from docstrings
    "sphinx.ext.napoleon",  # Google/NumPy style docstrings
    "sphinx.ext.viewcode",  # Add links to source code
    "sphinx.ext.intersphinx",  # Link to other Sphinx docs
    "sphinx.ext.todo",  # Support for TODO items
    "sphinx.ext.coverage",  # Doc coverage stats
    "sphinx.ext.mathjax",  # Math rendering for cognitive docs
    "sphinx_autodoc_typehints",  # Type hints support
    "sphinx.ext.autosummary",  # Create summaries
    "myst_parser",  # Markdown parser
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__,Config",
    "show-inheritance": True,
}
autodoc_mock_imports = [
    "django",
    "ninja",
    "redis",
    "kafka",
    "milvus",
    "numpy",
    "torch",
    "transformers",
    "pydantic",
    "httpx",
    "somabrain.storage.feedback",
    "somabrain.storage.token_ledger",
    "somabrain.runtime",
    "somabrain.storage",
    "somabrain.api.v1",
    "somabrain.saas.webhooks",
    "somabrain.api.endpoints.oak",
]

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "django": (
        "https://docs.djangoproject.com/en/5.0/",
        "https://docs.djangoproject.com/en/5.0/_objects/",
    ),
}

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
}

html_static_path = ["_static"]
html_css_files = ["custom.css"]  # YACHAQ brand styling
html_title = "SomaBrain Documentation"
html_short_title = "SomaBrain"

# -- Extension configuration -------------------------------------------------
todo_include_todos = True

# Source settings
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Suppress lexer warnings for code blocks
highlight_language = "python3"
suppress_warnings = [
    "misc.highlighting_failure",
    "toc.circular",
    "toc.secnum",
    "autodoc.import_object",
    "myst.xref_missing",
]
