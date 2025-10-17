# Integration Run Guide

1. Activate virtualenv: `source venv/bin/activate` (or your env).
2. Export vars: `export SOMABRAIN_STRICT_REAL=1`, `export SOMABRAIN_KAFKA_PORT=9092`, `export SOMABRAIN_REDIS_PORT=6379`.
3. Run focused tests: `python -m pytest tests/test_config_api.py tests/test_memory_api.py tests/test_tiered_memory_registry.py tests/test_journal_to_outbox.py`
4. Optional: `python -m pytest` for full suite.

Artifacts generated today:
- `launch_band_script.json`
- `integration_run.md`
