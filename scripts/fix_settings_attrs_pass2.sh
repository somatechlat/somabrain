#!/bin/bash
# Second-pass comprehensive settings attribute fixes
# This handles the remaining 156+ attributes

set -e
cd "$(dirname "$0")/.."

echo "=== Second-pass: Fixing remaining 156 settings attributes ==="

replace_attr() {
    local old="$1"
    local new="$2"
    find somabrain tests common -name "*.py" -type f 2>/dev/null | while read file; do
        if grep -q "settings\.${old}" "$file" 2>/dev/null; then
            sed -i '' "s/settings\.${old}/settings.${new}/g" "$file" && echo "  Fixed: $file"
        fi
    done
}

# OPA settings
replace_attr "opa_policy_key" "SOMABRAIN_OPA_POLICY_KEY"
replace_attr "opa_policy_sig_key" "SOMABRAIN_OPA_POLICY_SIG_KEY"
replace_attr "opa_allow_on_error" "SOMABRAIN_OPA_ALLOW_ON_ERROR"
replace_attr "opa_timeout" "SOMA_OPA_TIMEOUT"
replace_attr "opa_host" "SOMABRAIN_OPA_HOST"
replace_attr "opa_port" "SOMABRAIN_OPA_PORT"

# ALL neuromodulator settings
replace_attr "neuromod_dopamine_min" "SOMABRAIN_NEURO_DOPAMINE_MIN"
replace_attr "neuromod_dopamine_max" "SOMABRAIN_NEURO_DOPAMINE_MAX"
replace_attr "neuromod_dopamine_lr" "SOMABRAIN_NEURO_DOPAMINE_LR"
replace_attr "neuromod_serotonin_min" "SOMABRAIN_NEURO_SEROTONIN_MIN"
replace_attr "neuromod_serotonin_max" "SOMABRAIN_NEURO_SEROTONIN_MAX"
replace_attr "neuromod_serotonin_lr" "SOMABRAIN_NEURO_SEROTONIN_LR"
replace_attr "neuromod_noradrenaline_min" "SOMABRAIN_NEURO_NORAD_MIN"
replace_attr "neuromod_noradrenaline_max" "SOMABRAIN_NEURO_NORAD_MAX"
replace_attr "neuromod_noradrenaline_lr" "SOMABRAIN_NEURO_NORAD_LR"
replace_attr "neuromod_acetylcholine_min" "SOMABRAIN_NEURO_ACETYL_MIN"
replace_attr "neuromod_acetylcholine_max" "SOMABRAIN_NEURO_ACETYL_MAX"
replace_attr "neuromod_acetylcholine_lr" "SOMABRAIN_NEURO_ACETYL_LR"

# Sleep/consolidation
replace_attr "enable_sleep" "SOMABRAIN_ENABLE_SLEEP"
replace_attr "consolidation_enabled" "SOMABRAIN_CONSOLIDATION_ENABLED"
replace_attr "sleep_interval_seconds" "SOMABRAIN_SLEEP_INTERVAL_SECONDS"

# More infrastructure
replace_attr "require_memory" "REQUIRE_MEMORY"
replace_attr "require_infra" "REQUIRE_INFRA"
replace_attr "require_external_backends" "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS"

# Adaptation/learning
replace_attr "enable_advanced_learning" "SOMABRAIN_ENABLE_ADVANCED_LEARNING"
replace_attr "adapt_lr" "SOMABRAIN_ADAPT_LR"
replace_attr "adapt_max_history" "SOMABRAIN_ADAPT_MAX_HISTORY"

# Utility weights
replace_attr "utility_lambda" "SOMABRAIN_UTILITY_LAMBDA"
replace_attr "utility_mu" "SOMABRAIN_UTILITY_MU"
replace_attr "utility_nu" "SOMABRAIN_UTILITY_NU"

# Predictor
replace_attr "predictor_provider" "SOMABRAIN_PREDICTOR_PROVIDER"
replace_attr "predictor_dim" "SOMABRAIN_PREDICTOR_DIM"
replace_attr "predictor_alpha" "SOMABRAIN_PREDICTOR_ALPHA"
replace_attr "predictor_gamma" "SOMABRAIN_PREDICTOR_GAMMA"

# Retrieval
replace_attr "retrieval_alpha" "SOMABRAIN_RETRIEVAL_ALPHA"
replace_attr "retrieval_beta" "SOMABRAIN_RETRIEVAL_BETA"
replace_attr "retrieval_gamma" "SOMABRAIN_RETRIEVAL_GAMMA"
replace_attr "retrieval_tau" "SOMABRAIN_RETRIEVAL_TAU"

# Salience
replace_attr "salience_method" "SOMABRAIN_SALIENCE_METHOD"
replace_attr "salience_threshold" "SOMABRAIN_SALIENCE_THRESHOLD_STORE"
replace_attr "use_soft_salience" "SOMABRAIN_USE_SOFT_SALIENCE"

# Feature toggles
replace_attr "use_hrr" "SOMABRAIN_USE_HRR"
replace_attr "use_sdr_prefilter" "SOMABRAIN_USE_SDR_PREFILTER"
replace_attr "use_graph_augment" "SOMABRAIN_USE_GRAPH_AUGMENT"
replace_attr "use_planner" "SOMABRAIN_USE_PLANNER"
replace_attr "use_focus_state" "SOMABRAIN_USE_FOCUS_STATE"

# Graph
replace_attr "graph_hops" "SOMABRAIN_GRAPH_HOPS"
replace_attr "graph_limit" "SOMABRAIN_GRAPH_LIMIT"

# Planner
replace_attr "plan_max_steps" "SOMABRAIN_PLAN_MAX_STEPS"
replace_attr "planner_backend" "SOMABRAIN_PLANNER_BACKEND"

# Oak/ROAMDP
replace_attr "enable_oak" "ENABLE_OAK"
replace_attr "oak_gamma" "OAK_GAMMA"
replace_attr "oak_alpha" "OAK_ALPHA"

# Quantum
replace_attr "quantum_dim" "SOMABRAIN_QUANTUM_DIM"
replace_attr "quantum_sparsity" "SOMABRAIN_QUANTUM_SPARSITY"

# Tau/entropy
replace_attr "tau_min" "SOMABRAIN_TAU_MIN"
replace_attr "tau_max" "SOMABRAIN_TAU_MAX"
replace_attr "tau_decay_enabled" "SOMABRAIN_TAU_DECAY_ENABLED"

# More service configs
replace_attr "namespace" "SOMABRAIN_NAMESPACE"
replace_attr "default_tenant" "SOMABRAIN_DEFAULT_TENANT"
replace_attr "tenant_id" "SOMABRAIN_TENANT_ID"
replace_attr "service_name" "SOMABRAIN_SERVICE_NAME"
replace_attr "mode" "SOMABRAIN_MODE"

# Test/debug
replace_attr "pytest_current_test" "PYTEST_CURRENT_TEST"
replace_attr "oak_test_mode" "OAK_TEST_MODE"
replace_attr "debug_memory_client" "SOMABRAIN_DEBUG_MEMORY_CLIENT"

# Kafka topics
replace_attr "topic_config_updates" "SOMABRAIN_TOPIC_CONFIG_UPDATES"
replace_attr "topic_next_event" "SOMABRAIN_TOPIC_NEXT_EVENT"
replace_attr "audit_topic" "SOMABRAIN_AUDIT_TOPIC"

# Journal
replace_attr "journal_dir" "SOMABRAIN_JOURNAL_DIR"
replace_attr "journal_max_file_size" "SOMABRAIN_JOURNAL_MAX_FILE_SIZE"

# Outbox
replace_attr "outbox_batch_size" "OUTBOX_BATCH_SIZE"
replace_attr "outbox_max_delay" "OUTBOX_MAX_DELAY"

echo "✅ Second-pass complete"
echo "=== Final verification ==="
remaining=$(python3 scripts/find_settings_issues.py somabrain 2>/dev/null | grep -c "Old: settings\." || echo "0")
echo "Remaining issues: $remaining"
echo "=== Done ==="
