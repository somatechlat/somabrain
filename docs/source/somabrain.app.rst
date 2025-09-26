somabrain.app
===============

Lightweight, hand-authored API reference for ``somabrain.app`` used in the
documentation build to avoid importing runtime modules during doc generation.

This page intentionally provides a concise summary and links rather than
automatically importing the live module. For the authoritative runtime API
see the code under ``somabrain/app.py`` in the repository.

- create_app() -> returns a FastAPI application (runtime)
- start background workers and supervisors

See the code for full details; this page avoids importing the runtime module
so the docs build is robust in CI environments.
