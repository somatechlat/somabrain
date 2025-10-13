> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Test Server Strategy

This project uses a real FastAPI server (no mocks) for integration tests.

## Port Selection (9797)
We reserve `127.0.0.1:9797` for the integration test server to avoid collisions with any developer instance that may already be using the conventional port (9696). The test fixture in `tests/conftest.py`:

- Sets `SOMA_API_URL` to `http://127.0.0.1:9797` if not already defined.
- Starts a real `uvicorn somabrain.app:app` subprocess (no in-process TestClient shim) so behavior matches production wiring.
- Forces `SOMABRAIN_MINIMAL_PUBLIC_API=0` so the full public API (including `/constitution/version`) is available.

Override the port or base URL by exporting `SOMA_API_URL` before running `pytest`:

```bash
export SOMA_API_URL=http://127.0.0.1:9888
pytest -q
```

## Minimal Public API Mode
If you need to simulate minimal mode in a specific test run, set:

```bash
export SOMABRAIN_MINIMAL_PUBLIC_API=1
```

The `/health` endpoint now returns a `minimal_public_api` boolean so you can assert the active mode.

## Redis Backend (Strict Real Mode)
Strict mode (`SOMABRAIN_STRICT_REAL=1`) forbids patching Redis with in-memory emulators. A real Redis
instance must be reachable or tests that rely on Redis-backed features will fail fast with a
diagnostic message.

Local development:
```bash
docker run -p 6379:6379 redis:7-alpine
export SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379/0
pytest -q
```

Bypassing strict realism (NOT for CI/prod) to allow legacy fakeredis path:
```bash
export SOMABRAIN_STRICT_REAL_BYPASS=1   # test fixture then allows fakeredis if installed
pytest -q
```

## Troubleshooting 404 on /constitution/version
If you see a 404:
- Confirm test logs show a line like: `[tests.conftest] SOMA_API_URL=http://127.0.0.1:9797`.
- Curl the endpoint manually: `curl -i $SOMA_API_URL/constitution/version`.
- Check `/health` for `minimal_public_api`.
- Ensure another process isn’t binding the port (use `lsof -i TCP:9797`).

## Rationale
- Real subprocess uvicorn ensures lifecycle, middleware ordering, and import-time side effects match production.
- Fixed port (9797) with explicit override reduces port collision flakiness.
- Strict realism surfaces hidden dependencies early instead of masking them with stubs.

## Future Enhancements
- Optional ephemeral port mode that writes the chosen port to a `.pytest_server_port` file for multi-process coordination.
- Add a lightweight `tests/tools/print_routes.py` to snapshot routes if coverage needs expand.

Feel free to extend this document as new integration components are added. For full environment and
mode reference see `../CONFIGURATION.md`.
