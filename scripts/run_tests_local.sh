#!/bin/bash
set -e
echo "🚀 Starting Test Runner..."

export DJANGO_SETTINGS_MODULE=somabrain.settings

# Load .env manually - robust loop
if [ -f .env ]; then
  echo "📄 Loading .env file..."
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]]; then
       # naive export, might fail on complex values but better than xargs
       export "$line" || true
    fi
  done < .env
fi

echo "✅ Environment loaded."

# Explicit overrides for local testing against Docker
export SOMA_MILVUS_PORT=20530
export SOMABRAIN_MILVUS_PORT=20530
export MILVUS_PORT=20530
export SOMABRAIN_OPA_URL=http://localhost:20181
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:10101
export SOMABRAIN_MEMORY_HTTP_TOKEN="${SOMABRAIN_MEMORY_HTTP_TOKEN:-}"
export SOMA_API_TOKEN="${SOMA_API_TOKEN:-${SOMABRAIN_MEMORY_HTTP_TOKEN:-}}"

echo "🔍 Verifying Critical Env Vars:"
echo "   SOMA_MILVUS_PORT=$SOMA_MILVUS_PORT"
echo "   SOMABRAIN_OPA_URL=$SOMABRAIN_OPA_URL"

echo "🧪 Executing Pytest..."
.venv/bin/pytest tests/ -v -W ignore
echo "🏁 Tests Complete."
