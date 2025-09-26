API Reference
==============

This section is generated dynamically from the codebase using Sphinx autodoc
and autosummary. It lists the main public API modules and their documented
members. Regenerate the docs locally with `make html` or the sphinx command.

.. note::
   The API reference is curated manually in this project to avoid Sphinx
   autosummary-driven imports during builds. API pages are linked explicitly
   below.

.. toctree::
   :maxdepth: 1

   somabrain.app
   somabrain.thalamus
   _autosummary/somabrain.api.routers.link
   _autosummary/somabrain.api.routers.persona
   _autosummary/somabrain.api.routers.rag
   _autosummary/somabrain.app
   _autosummary/somabrain.thalamus

.. note::
   If autosummary fails due to heavy runtime imports, the Sphinx config uses
   `autodoc_mock_imports` and a lightweight `docs/_stubs` directory to avoid
   import-time side effects. If additional modules require mocking, add them
   to `autodoc_mock_imports` in `conf.py`.
