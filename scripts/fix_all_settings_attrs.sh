#!/bin/bash
# Comprehensive settings attribute replacement script
# Converts all Pydantic snake_case to Django UPPERCASE

set -e
cd "$(dirname "$0")/.."

echo "=== Fixing 268 settings attribute access patterns ==="

# Function to replace in all Python files
replace_attr() {
    local old="$1"
    local new="$2"
    find somabrain tests common -name "*.py" -type f 2>/dev/null | while read file; do
        if grep -q "settings\.${old}" "$file" 2>/dev/null; then
            sed -i '' "s/settings\.${old}/settings.${new}/g" "$file"
        fi
    done
}

# Common attributes - comprehensive list
replace_attr "postgres_dsn" "SOMABRAIN_POSTGRES_DSN"
replace_attr "log_level" "SOMABRAIN_LOG_LEVEL"
replace_attr "redis_url" "SOMABRAIN_REDIS_URL"
replace_attr "kafka_bootstrap_servers" "KAFKA_BOOTSTRAP_SERVERS"
replace_attr "jwt_secret" "SOMABRAIN_JWT_SECRET"
replace_attr "opa_url" "SOMABRAIN_OPA_URL"
replace_attr "memory_http_endpoint" "SOMABRAIN_MEMORY_HTTP_ENDPOINT"
replace_attr "memory_http_token" "SOMABRAIN_MEMORY_HTTP_TOKEN"
replace_attr "milvus_host" "MILVUS_HOST"
replace_attr "milvus_port" "MILVUS_PORT"
replace_attr "milvus_collection" "MILVUS_COLLECTION"

# Memory settings
replace_attr "wm_size" "SOMABRAIN_WM_SIZE"
replace_attr "wm_alpha" "SOMABRAIN_WM_ALPHA"
replace_attr "wm_beta" "SOMABRAIN_WM_BETA"
replace_attr "wm_gamma" "SOMABRAIN_WM_GAMMA"
replace_attr "wm_recency_time_scale" "SOMABRAIN_WM_RECENCY_TIME_SCALE"
replace_attr "wm_recency_max_steps" "SOMABRAIN_WM_RECENCY_MAX_STEPS"
replace_attr "wm_salience_threshold" "SOMABRAIN_WM_SALIENCE_THRESHOLD"
replace_attr "wm_per_col_min_capacity" "SOMABRAIN_WM_PER_COL_MIN_CAPACITY"
replace_attr "wm_vote_softmax_floor" "SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR"
replace_attr "wm_vote_entropy_eps" "SOMABRAIN_WM_VOTE_ENTROPY_EPS"
replace_attr "wm_per_tenant_capacity" "SOMABRAIN_WM_PER_TENANT_CAPACITY"
replace_attr "mtwm_max_tenants" "SOMABRAIN_MTWM_MAX_TENANTS"

# Micro-circuits
replace_attr "micro_circuits" "SOMABRAIN_MICRO_CIRCUITS"
replace_attr "micro_vote_temperature" "SOMABRAIN_MICRO_VOTE_TEMPERATURE"
replace_attr "micro_max_tenants" "SOMABRAIN_MICRO_MAX_TENANTS"
replace_attr "use_microcircuits" "SOMABRAIN_USE_MICROCIRCUITS"

# HRR/SDR/Cognitive
replace_attr "hrr_dim" "SOMABRAIN_HRR_DIM"
replace_attr "hrr_dtype" "SOMABRAIN_HRR_DTYPE"
replace_attr "hrr_renorm" "SOMABRAIN_HRR_RENORM"
replace_attr "hrr_vector_family" "SOMABRAIN_HRR_VECTOR_FAMILY"
replace_attr "bhdc_sparsity" "SOMABRAIN_BHDC_SPARSITY"
replace_attr "sdr_dim" "SOMABRAIN_SDR_DIM"
replace_attr "sdr_bits" "SOMABRAIN_SDR_BITS"
replace_attr "sdr_density" "SOMABRAIN_SDR_DENSITY"
replace_attr "sdr_sparsity" "SOMABRAIN_SDR_SPARSITY"
replace_attr "context_budget_tokens" "SOMABRAIN_CONTEXT_BUDGET_TOKENS"
replace_attr "max_superpose" "SOMABRAIN_MAX_SUPERPOSE"
replace_attr "default_wm_slots" "SOMABRAIN_DEFAULT_WM_SLOTS"
replace_attr "global_seed" "SOMABRAIN_GLOBAL_SEED"
replace_attr "determinism" "SOMABRAIN_DETERMINISM"

# Quotas
replace_attr "quota_tenant" "SOMABRAIN_QUOTA_TENANT" 
replace_attr "quota_tool" "SOMABRAIN_QUOTA_TOOL"
replace_attr "quota_action" "SOMABRAIN_QUOTA_ACTION"

# Circuit breaker
replace_attr "circuit_failure_threshold" "SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD"
replace_attr "circuit_reset_interval" "SOMABRAIN_CIRCUIT_RESET_INTERVAL"
replace_attr "circuit_cooldown_interval" "SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL"

# Neuromodulators
replace_attr "neuromod_dopamine_base" "SOMABRAIN_NEURO_DOPAMINE_BASE"
replace_attr "neuromod_serotonin_base" "SOMABRAIN_NEURO_SEROTONIN_BASE"
replace_attr "neuromod_noradrenaline_base" "SOMABRAIN_NEURO_NORAD_BASE"
replace_attr "neuromod_acetylcholine_base" "SOMABRAIN_NEURO_ACETYL_BASE"

# Service settings
replace_attr "feature_flags_port" "SOMABRAIN_FEATURE_FLAGS_PORT"
replace_attr "calibration_enabled" "CALIBRATION_ENABLED"
replace_attr "learning_tenants_file" "SOMABRAIN_LEARNING_TENANTS_FILE"
replace_attr "learning_tenants_config" "LEARNING_TENANTS_CONFIG"
replace_attr "learner_dlq_path" "SOMABRAIN_LEARNER_DLQ_PATH"
replace_attr "learner_dlq_topic" "SOMABRAIN_LEARNER_DLQ_TOPIC"
replace_attr "spectral_cache_dir" "SOMABRAIN_SPECTRAL_CACHE_DIR"

# Tiered memory
replace_attr "tiered_memory_cleanup_backend" "SOMABRAIN_CLEANUP_BACKEND"
replace_attr "tiered_memory_cleanup_topk" "SOMABRAIN_CLEANUP_TOPK"
replace_attr "tiered_memory_cleanup_hnsw_m" "SOMABRAIN_CLEANUP_HNSW_M"
replace_attr "tiered_memory_cleanup_hnsw_ef_construction" "SOMABRAIN_CLEANUP_HNSW_EF_CONSTRUCTION"
replace_attr "tiered_memory_cleanup_hnsw_ef_search" "SOMABRAIN_CLEANUP_HNSW_EF_SEARCH"

# Infrastructure
replace_attr "health_port" "HEALTH_PORT"
replace_attr "api_url" "SOMABRAIN_API_URL"
replace_attr "hostname" "SOMABRAIN_HOST"
replace_attr "public_host" "SOMABRAIN_HOST"
replace_attr "public_port" "SOMABRAIN_PORT"
replace_attr "api_scheme" "SOMABRAIN_API_SCHEME"

# Embed dim
replace_attr "embed_dim" "EMBED_DIM"

echo "✅ Completed attribute replacements"
echo "=== Verifying remaining snake_case attributes ==="

# Count remaining issues
remaining=$(python3 scripts/find_settings_issues.py somabrain 2>/dev/null | grep -c "Old: settings\." || echo "0")
echo "Remaining issues: $remaining"

echo "=== Done ==="
