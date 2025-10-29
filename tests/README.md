# SomaBrain Test Running Cheatsheet

A concise, canonical reference for running tests locally and in CI-like dev environments.

## Prerequisites

- Python 3.11+
- Install dev dependencies from the repo root:

```sh
python -m pip install -U pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

- Recommended: copy `config/env.example` to `.env` and adjust for your machine/services.

Key environment variables (see `config/env.example`):
- `SOMABRAIN_API_URL` (or `SOMA_API_URL`): API base (e.g., http://127.0.0.1:9696)
- `SOMABRAIN_MEMORY_HTTP_ENDPOINT`: external Memory HTTP service (e.g., http://127.0.0.1:9595)
- `SOMABRAIN_REDIS_URL`: redis URL for certain tests (optional)
- `SOMABRAIN_DEFAULT_TENANT`: default tenant header value used by tests
- `SOMA_API_URL_LOCK_BYPASS=1`: bypass eager reachability skip (forces attempting the target even if probes fail)

## Test markers

Available pytest markers (see `pytest.ini` and tests):
- `unit` — fast, isolated
- `integration` — live endpoints/backends (API, Memory, Redis)
- `learning` — persistence/learning sensitive (subset of integration)
- `e2e`, `slow`, `benchmark` — as labeled in individual tests

List registered markers:

```sh
pytest --markers
```

## Quick commands

- Run everything (quiet):

```sh
pytest -q
```

- Only unit tests:

```sh
pytest -q -m unit
```

- Integration tests (skip learning-sensitive cases):

```sh
# Ensure your live stack is up and external Memory (9595) is reachable first
export SOMABRAIN_API_URL=http://127.0.0.1:9696
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
pytest -q -m "integration and not learning"
```

- Full integration including learning-sensitive:

```sh
export SOMABRAIN_API_URL=http://127.0.0.1:9696
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
pytest -q -m integration
```

- Single file / single test:

```sh
pytest -q tests/integration/test_e2e_memory_http.py::TestE2EMemoryHTTP::test_remember_and_recall_end_to_end -k "not slow"
```

## Lint, type check, and coverage

- Ruff (strict config present in repo):

```sh
ruff check . --config ruff_strict.toml
```

- mypy:

```sh
mypy . --config mypy.ini
```

- Pytest with coverage reports:

```sh
pytest -q --cov=somabrain --cov-report=term-missing --cov-report=html:htmlcov
```

## Troubleshooting

- API health fails at 9999: many dev profiles expose the API on 9696. Verify with `/health` and export `SOMABRAIN_API_URL=http://127.0.0.1:9696`.
- Memory backend required: tests marked `integration` assume a real Memory HTTP service on `:9595`. Start it and export `SOMABRAIN_MEMORY_HTTP_ENDPOINT`.
- Flaky reachability during bring-up: set `SOMA_API_URL_LOCK_BYPASS=1` to skip eager skips while you iterate, or re-run after services are ready.
- Tenant headers: tests default to `SOMABRAIN_DEFAULT_TENANT` (e.g., `sandbox`). Ensure your stack recognizes this tenant or override per test.
- Missing extras (redis, fastavro): some tests are skipped when optional deps aren’t installed. Install optional deps if you need the full suite.

## See also

- Benchmarks overview and live/micro commands: `benchmarks/README.md`
- Operator-focused walkthrough: `docs/technical-manual/benchmarks-quickstart.md`
- Developer testing standards: `docs/development-manual/testing-guidelines.md`
