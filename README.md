# SomaBrain

SomaBrain is a research platform for exploring long-horizon cognitive agents. The
project bundles the core FastAPI service, supporting infrastructure components
such as Redis, Kafka, and OPA, plus a growing suite of benchmarks and
observability tooling.

## Getting Started

1. Create a Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e .[dev]
   ```
2. Run the unit test suite:
   ```bash
   pytest
   ```

## Local Development Environment

To launch the lightweight development stack (API + Redis + OPA):

```bash
./scripts/start_dev_infra.sh
```

The API will be served on `http://localhost:9696` with health check
`http://localhost:9696/health`.

## Project Structure

```
common/       Shared helpers used across services
memory/       Memory subsystem powering recall/remember endpoints
somabrain/    FastAPI application routers and runtime wiring
tests/        Pytest suite covering core API flows
```

## Contributing

Please run formatting and type checks before opening a pull request:

```bash
ruff check
mypy
pytest
```

Open an issue to discuss larger changes or architectural design questions.
