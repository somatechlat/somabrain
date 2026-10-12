#!/bin/sh
# Run somabrain memory/recall/learning tests against REAL infra.
# Topology: live Vault + live Postgres + live Rust core. No mocks.
set -eu
cd /Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain

PW=$(docker run --rm --network somabrain_somabrain_standalone_net \
  --volumes-from somabrain_standalone_vault_unseal_watch \
  python:3.12-slim python -c "
import urllib.request,json
tok=open('/run/t0/vault_root_token').read().strip()
req=urllib.request.Request('http://somabrain_standalone_vault:8200/v1/somabrain/data/database',headers={'X-Vault-Token':tok})
d=json.load(urllib.request.urlopen(req,timeout=5))
print((d.get('data') or {}).get('data',{}).get('password',''))
" 2>/dev/null)

TOKENFILE=$(mktemp)
docker run --rm -v somabrain_t0_ram:/run/t0:ro alpine:3.19 cat /run/t0/vault_root_token > "$TOKENFILE" 2>/dev/null

export TEST_PG_DSN="postgresql://somabrain:${PW}@127.0.0.1:30106/somabrain"
export VAULT_ADDR="http://127.0.0.1:30200"
export VAULT_TOKEN_FILE="$TOKENFILE"
export SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://127.0.0.1:30101"
export EMBED_DIM=768
export SOMABRAIN_EMBED_DIM=768
export TEST_PG_USER=somabrain
export TEST_PG_HOST=127.0.0.1
export TEST_PG_PORT=30106
export TEST_PG_DB=somabrain
export TEST_PG_PASSWORD="$PW"
export DJANGO_SETTINGS_MODULE="tests.unit.test_settings"
export ALLOWED_HOSTS="localhost,127.0.0.1,testserver"
export SOMABRAIN_NAMESPACE=test-ns

echo "PW-LEN=${#PW} DSN=$TEST_PG_DSN"

exec .venv/bin/python -m pytest \
  tests/unit/test_learning_math.py \
  tests/unit/test_apm_memory_learning.py \
  tests/unit/test_agent_interaction_learning.py \
  tests/unit/test_w3_anneal_gains_entropy.py \
  tests/unit/test_adv1_scoring_fixes.py \
  tests/unit/test_search_ranking_one_space.py \
  tests/unit/test_promotion_async_safety.py \
  tests/unit/test_store_fields_sfm.py \
  tests/unit/test_memory_type_contract.py \
  tests/unit/test_recall_degraded_flag.py \
  tests/unit/test_recall_fail_closed.py \
  tests/unit/memory/test_store_fields.py \
  tests/unit/test_wm_eviction_metadata.py \
  --reuse-db --no-migrations \
  -q --tb=line "$@"
