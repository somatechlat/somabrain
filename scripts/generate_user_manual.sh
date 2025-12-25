#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# generate_user_manual.sh
# ---------------------------------------------------------------------------
# This script builds the human‑readable documentation (Sphinx HTML) and also
# produces a machine‑oriented OpenAPI specification for the SomaBrain API.
# It is intended to be run as a background job (e.g. via `nohup` or a cron
# entry) so that the documentation stays up‑to‑date with the latest code.
# ---------------------------------------------------------------------------

set -euo pipefail

# Log file – adjust path as needed.
LOG_FILE="${HOME}/somabrain_user_manual.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') [START] Generating user manual" >> "$LOG_FILE"

# ---------------------------------------------------------------------------
# 1. Build Sphinx documentation (human‑readable).
# ---------------------------------------------------------------------------
if command -v sphinx-build >/dev/null 2>&1; then
    # The repository uses the docs/ source layout. Build HTML output into
    # docs/build/html. Errors are appended to the log.
    sphinx-build -b html docs/source docs/build/html >> "$LOG_FILE" 2>&1
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Sphinx HTML built successfully" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] sphinx-build not found – skipping HTML docs" >> "$LOG_FILE"
fi

# ---------------------------------------------------------------------------
# 2. Export OpenAPI JSON (machine‑readable).
# ---------------------------------------------------------------------------
# The FastAPI app exposes its OpenAPI schema at /openapi.json. We assume the
# service is already running on the canonical port (default 9696). If the
# endpoint is unavailable we log the failure but do not abort the script.
OPENAPI_URL="http://127.0.0.1:9696/openapi.json"
OPENAPI_DEST="docs/openapi.json"

if curl -sSf "$OPENAPI_URL" -o "$OPENAPI_DEST"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] OpenAPI spec saved to $OPENAPI_DEST" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] Failed to fetch OpenAPI spec from $OPENAPI_URL" >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') [END] User manual generation completed" >> "$LOG_FILE"
