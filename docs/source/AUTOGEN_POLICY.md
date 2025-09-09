# Autosummary / Generated docs policy

We generate API stub pages using Sphinx autosummary during documentation builds. Many of these generated pages duplicate the source-level docstrings and can create duplicate-object and orphan warnings when included in the published site.

Policy summary

- The canonical API documentation is `api.md` (Markdown, MyST) in this directory.
- Generated autosummary pages are intentionally excluded from the published site by default.
  - This prevents duplicate-object descriptions and keeps the site navigation focused.
- If you want a specific generated API page to appear in the site, either:
  1. Add the target page explicitly to a toctree (for example `modules.rst`), and
  2. Remove that specific path from `exclude_patterns` in `conf.py`.

How to surface a module in the docs

1. Create or update `docs/source/modules.rst` or `api_modules.rst` with the module names you want visible.
2. Remove the corresponding generated path from `exclude_patterns` in `conf.py`.
3. Re-run the Sphinx build.

This policy keeps generated stubs available for regeneration while avoiding noisy warnings in routine builds.
