> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Continuous Integration Strategy

## Pipeline

- Checkout → Python 3.11 (actions/setup-python)
- Install dev dependencies (`requirements-dev.txt`, includes Alembic, lint tools)
- Lint stage: `ruff check`, `black --check`
- Test stage: `alembic upgrade head`, `pytest tests/test_context_api.py tests/test_rag_integration.py`
- Export OpenAPI: `./scripts/export_openapi.py` -> pipeline artifact

## Notes
- SQLite fallback is used in CI via `SOMABRAIN_POSTGRES_DSN` pointing to `data/somabrain.db`.
- Extend the test matrix as more integration suites come online (S6+).
- Future work: add lint/jobs, Kafka smoke, load harness.
