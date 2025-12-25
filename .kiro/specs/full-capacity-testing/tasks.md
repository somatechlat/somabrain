# Implementation Tasks - SomaBrain Full Capacity Real-World Testing

## Code Quality Gate

**IMPORTANT**: After completing each task, run the following code quality checks:

```bash
# 1. Format with Black
black tests/proofs/ somabrain/ --check

# 2. Lint with Ruff
ruff check tests/proofs/ somabrain/

# 3. Type check with Pyright
pyright tests/proofs/ somabrain/
```

Fix any issues before marking the task complete.

---

## Phase 0: Test Infrastructure Setup

### Task 0.1: Create test directory structure
- [x] Create `tests/proofs/` directory with `__init__.py`
- [x] Create category subdirectories (category_a through category_g)
- [x] Create `tests/fixtures/` directory with `__init__.py`
- [x] **Requirement**: E1 (Docker Infrastructure Setup)

### Task 0.2: Create shared test fixtures
- [x] Create `tests/proofs/conftest.py` with session-scoped fixtures
- [x] Implement Docker health check fixtures
- [x] Implement tenant isolation fixtures
- [x] **Requirement**: E1, E2

### Task 0.3: Create golden dataset fixtures
- [x] Create `tests/fixtures/golden_datasets.py`
- [x] Define GoldenMemoryItem, GoldenTestSet, GoldenQuery dataclasses
- [x] Create 100-item golden test set with known relevance scores
- [x] **Requirement**: B2, G3


---

## Phase 1: Category A - Mathematical Core Proofs

### Task 1.1: HRR Binding Mathematical Correctness (A1)
- [x] Create `tests/proofs/category_a/test_hrr_math.py`
- [x] Implement `test_spectral_magnitude_bounded` - A1.1
- [x] Implement `test_role_unit_norm` - A1.2
- [x] Implement `test_bind_unbind_invertibility` - A1.3
- [x] Implement `test_superposition_recovery` - A1.4
- [x] Implement `test_wiener_filter_optimality` - A1.5
- [x] Use Hypothesis for property-based testing
- [x] **Run Black, Ruff, Pyright after completion**

### Task 1.2: Vector Similarity Mathematical Correctness (A2)
- [x] Create `tests/proofs/category_a/test_similarity_math.py`
- [x] Implement `test_symmetry` - A2.1
- [x] Implement `test_self_similarity` - A2.2
- [x] Implement `test_boundedness` - A2.3
- [x] Implement `test_zero_handling` - A2.4
- [x] Implement `test_normalization` - A2.5
- [x] Use Hypothesis for property-based testing
- [x] **Run Black, Ruff, Pyright after completion**

### Task 1.3: Predictor Mathematical Correctness (A3)
- [x] Create `tests/proofs/category_a/test_predictor_math.py`
- [x] Implement `test_chebyshev_convergence` - A3.1
- [x] Implement `test_lanczos_eigenvalue_bounds` - A3.2
- [x] Implement `test_mahalanobis_non_negativity` - A3.3
- [x] Implement `test_uncertainty_monotonicity` - A3.4
- [x] Implement `test_singular_covariance_handling` - A3.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 1.4: Salience Computation Correctness (A4)
- [x] Create `tests/proofs/category_a/test_salience_math.py`
- [x] Implement `test_weighted_formula` - A4.1
- [x] Implement `test_neuromodulator_modulation` - A4.2
- [x] Implement `test_fd_energy_bounds` - A4.3
- [x] Implement `test_soft_salience_bounds` - A4.4
- [x] Implement `test_hysteresis_margin` - A4.5
- [x] **Run Black, Ruff, Pyright after completion**

---

## Phase 2: Category E - Infrastructure Requirements

### Task 2.1: Docker Infrastructure Setup (E1)
- [x] Create `tests/proofs/category_e/test_docker_setup.py`
- [x] Implement `test_docker_compose_starts_all_services` - E1.1
- [x] Implement `test_redis_accessible_with_persistence` - E1.2
- [x] Implement `test_kafka_creates_topics` - E1.3
- [x] Implement `test_milvus_ready_for_vectors` - E1.4
- [x] Implement `test_postgres_migrations_apply` - E1.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 2.2: Service Health Verification (E2)
- [x] Create `tests/proofs/category_e/test_health_verification.py`
- [x] Implement `test_health_includes_all_backends` - E2.1
- [x] Implement `test_health_reports_degraded` - E2.2
- [x] Implement `test_prometheus_metrics_present` - E2.3
- [x] Implement `test_jaeger_traces_complete` - E2.4
- [x] Implement `test_opa_decisions_logged` - E2.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 2.3: Resilience Under Failure (E3)
- [x] Create `tests/proofs/category_e/test_resilience.py`
- [x] Implement `test_redis_unavailable_degraded_wm` - E3.1
- [x] Implement `test_kafka_unreachable_outbox_queues` - E3.2
- [x] Implement `test_milvus_slow_timeout_wm_only` - E3.3
- [x] Implement `test_postgres_retry_exponential_backoff` - E3.4
- [x] Implement `test_opa_unavailable_fail_closed` - E3.5
- [x] **Run Black, Ruff, Pyright after completion**


---

## Phase 3: Category B - Memory System Functional Proofs

### Task 3.1: Working Memory Capacity and Eviction (B1)
- [x] Create `tests/proofs/category_b/test_wm_capacity.py`
- [x] Implement `test_capacity_limit_enforced` - B1.1 (NOTE: actual impl uses salience-based eviction)
- [x] Implement `test_recency_set_on_admission` - B1.2
- [x] Implement `test_recency_decays_exponentially` - B1.3
- [x] Implement `test_duplicate_updates_existing` - B1.4
- [x] Implement `test_recall_ranking_by_similarity` - B1.5
- [x] **Run Black, Ruff, Pyright after completion**
- **NOTE**: WM now uses salience-based eviction with exponential recency decay and duplicate detection

### Task 3.2: Long-Term Memory Vector Search (B2)
- [x] Create `tests/proofs/category_b/test_ltm_search.py`
- [x] Implement `test_ann_returns_top1_for_identical` - B2.1
- [x] Implement `test_returns_exactly_k_items` - B2.2
- [x] Implement `test_threshold_excludes_below` - B2.3
- [x] Implement `test_recall_at_10_above_95` - B2.4
- [x] Implement `test_vectors_normalized_before_storage` - B2.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 3.3: Memory Round-Trip Integrity (B3)
- [x] Create `tests/proofs/category_b/test_memory_roundtrip.py`
- [x] Implement `test_payload_survives_roundtrip` - B3.1
- [x] Implement `test_coordinate_deterministic` - B3.2
- [x] Implement `test_json_fields_exact` - B3.3
- [x] Implement `test_timestamp_precision` - B3.4
- [x] Implement `test_metadata_preserved` - B3.5
- [x] **Run Black, Ruff, Pyright after completion**
- **NOTE**: Also includes D1.1, D1.2 tenant isolation tests (security fix applied)

### Task 3.4: Retrieval Pipeline Fusion (B4)
- [x] Create `tests/proofs/category_b/test_fusion.py`
- [x] Implement `test_wm_ltm_merge_no_duplicates` - B4.1
- [x] Implement `test_fusion_weights_applied` - B4.2
- [x] Implement `test_one_source_fails_returns_other` - B4.3
- [x] Implement `test_graph_retrieval_boosts_relevance` - B4.4
- [x] Implement `test_diversity_reranking_coverage` - B4.5
- [x] **Run Black, Ruff, Pyright after completion**

---

## Phase 4: Category C - Cognitive Function Proofs

### Task 4.1: Neuromodulator State Management (C1)
- [x] Create `tests/proofs/category_c/test_neuromodulators.py`
- [x] Implement `test_dopamine_increases_reward_sensitivity` - C1.1
- [x] Implement `test_serotonin_shifts_exploitation` - C1.2
- [x] Implement `test_noradrenaline_narrows_attention` - C1.3
- [x] Implement `test_acetylcholine_increases_learning_rate` - C1.4
- [x] Implement `test_all_values_in_valid_range` - C1.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 4.2: Planning and Decision Making (C2)
- [x] Create `tests/proofs/category_c/test_planning.py`
- [x] Implement `test_options_ranked_by_utility` - C2.1
- [x] Implement `test_context_increases_relevance` - C2.2
- [x] Implement `test_equal_utility_tie_breaking` - C2.3
- [x] Implement `test_timeout_returns_best_so_far` - C2.4
- [x] Implement `test_no_options_returns_empty` - C2.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 4.3: Learning and Adaptation (C3)
- [x] Create `tests/proofs/category_c/test_learning.py`
- [x] Implement `test_positive_feedback_increases_weights` - C3.1
- [x] Implement `test_negative_feedback_decreases_weights` - C3.2
- [x] Implement `test_constraints_clamp_values` - C3.3
- [x] Implement `test_tau_annealing_decay` - C3.4
- [x] Implement `test_state_persists_across_restart` - C3.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 4.4: Context and Attention (C4)
- [x] Create `tests/proofs/category_c/test_context.py`
- [x] Implement `test_anchors_create_hrr_binding` - C4.1
- [x] Implement `test_context_decays_over_time` - C4.2
- [x] Implement `test_attention_prioritizes_retrieval` - C4.3
- [x] Implement `test_clear_resets_to_neutral` - C4.4
- [x] Implement `test_saturation_prunes_oldest` - C4.5
- [x] **Run Black, Ruff, Pyright after completion**


---

## Phase 5: Category D - Multi-Tenant Isolation Proofs

### Task 5.1: Memory Isolation (D1)
- [x] Create `tests/proofs/category_d/test_memory_isolation.py`
- [x] Implement `test_tenant_a_invisible_to_tenant_b` - D1.1
- [x] Implement `test_cross_tenant_query_returns_empty` - D1.2
- [x] Implement `test_namespace_scopes_queries` - D1.3
- [x] Implement `test_missing_header_uses_default` - D1.4
- [x] Implement `test_100_tenants_zero_leakage` - D1.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 5.2: State Isolation (D2)
- [x] Create `tests/proofs/category_d/test_state_isolation.py`
- [x] Implement `test_neuromodulator_isolation` - D2.1
- [x] Implement `test_circuit_breaker_isolation` - D2.2
- [x] Implement `test_quota_isolation` - D2.3
- [x] Implement `test_adaptation_isolation` - D2.4
- [x] Implement `test_wm_capacity_isolation` - D2.5
- [x] **Run Black, Ruff, Pyright after completion**

---

## Phase 6: Category F - Circuit Breaker and Fault Tolerance Proofs

### Task 6.1: Circuit Breaker State Machine (F1)
- [x] Create `tests/proofs/category_f/test_circuit_state_machine.py`
- [x] Implement `test_closed_to_open_on_threshold` - F1.1
- [x] Implement `test_open_fails_fast` - F1.2
- [x] Implement `test_open_to_half_open_on_timeout` - F1.3
- [x] Implement `test_half_open_to_closed_on_success` - F1.4
- [x] Implement `test_half_open_to_open_on_failure` - F1.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 6.2: Per-Tenant Circuit Isolation (F2)
- [x] Create `tests/proofs/category_f/test_circuit_per_tenant.py`
- [x] Implement `test_tenant_a_circuit_independent` - F2.1
- [x] Implement `test_tenant_b_unaffected_by_a_open` - F2.2
- [x] Implement `test_reset_independent` - F2.3
- [x] Implement `test_multiple_tenants_independent_recovery` - F2.4
- [x] Implement `test_metrics_labeled_by_tenant` - F2.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 6.3: Degraded Mode Operation (F3)
- [x] Create `tests/proofs/category_f/test_degraded_mode.py`
- [x] Implement `test_ltm_open_returns_wm_only_degraded` - F3.1
- [x] Implement `test_backend_unavailable_queues_outbox` - F3.2
- [x] Implement `test_degraded_health_reports_status` - F3.3
- [x] Implement `test_recovery_replays_without_duplicates` - F3.4
- [x] Implement `test_replay_completes_pending_zero` - F3.5
- [x] **Run Black, Ruff, Pyright after completion**

---

## Phase 7: Category G - Performance and Load Proofs

### Task 7.1: Latency SLOs (G1)
- [x] Create `tests/proofs/category_g/test_latency_slo.py`
- [x] Implement `test_remember_p95_under_300ms` - G1.1
- [x] Implement `test_recall_p95_under_400ms` - G1.2
- [x] Implement `test_plan_suggest_p95_under_1000ms` - G1.3
- [x] Implement `test_health_p99_under_100ms` - G1.4
- [x] Implement `test_neuromodulators_p95_under_50ms` - G1.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 7.2: Throughput Capacity (G2)
- [x] Create `tests/proofs/category_g/test_throughput.py`
- [x] Implement `test_100_concurrent_99_success` - G2.1
- [x] Implement `test_1000_memories_10s_no_loss` - G2.2
- [x] Implement `test_500_recalls_10s_complete` - G2.3
- [x] Implement `test_30min_sustained_stable_memory` - G2.4
- [x] Implement `test_spike_recovery_30s` - G2.5
- [x] **Run Black, Ruff, Pyright after completion**

### Task 7.3: Recall Quality Under Scale (G3)
- [x] Create `tests/proofs/category_g/test_recall_quality.py`
- [x] Implement `test_10k_corpus_precision_at_10` - G3.1
- [x] Implement `test_100k_corpus_recall_at_10` - G3.2
- [x] Implement `test_ndcg_at_10_above_75` - G3.3
- [x] Implement `test_diversity_pairwise_below_90` - G3.4
- [x] Implement `test_freshness_recency_weighted` - G3.5
- [x] **Run Black, Ruff, Pyright after completion**


---

## Acceptance Criteria Traceability Matrix

| Req ID | Acceptance Criteria | Test File | Test Method |
|--------|---------------------|-----------|-------------|
| A1.1 | Spectral magnitude bounded [0.9, 1.1] | test_hrr_math.py | test_spectral_magnitude_bounded |
| A1.2 | Role unit norm = 1.0 ± 1e-6 | test_hrr_math.py | test_role_unit_norm |
| A1.3 | Bind/unbind similarity > 0.95 | test_hrr_math.py | test_bind_unbind_invertibility |
| A1.4 | Superposition recovery > 0.8 | test_hrr_math.py | test_superposition_recovery |
| A1.5 | Wiener filter minimizes error | test_hrr_math.py | test_wiener_filter_optimality |
| A2.1 | Cosine symmetry | test_similarity_math.py | test_symmetry |
| A2.2 | Self-similarity = 1.0 | test_similarity_math.py | test_self_similarity |
| A2.3 | Bounded [-1, 1] | test_similarity_math.py | test_boundedness |
| A2.4 | Zero handling = 0.0 | test_similarity_math.py | test_zero_handling |
| A2.5 | Normalization L2 = 1.0 | test_similarity_math.py | test_normalization |
| A3.1 | Chebyshev convergence | test_predictor_math.py | test_chebyshev_convergence |
| A3.2 | Lanczos eigenvalue bounds | test_predictor_math.py | test_lanczos_eigenvalue_bounds |
| A3.3 | Mahalanobis ≥ 0 | test_predictor_math.py | test_mahalanobis_non_negativity |
| A3.4 | Uncertainty monotonic | test_predictor_math.py | test_uncertainty_monotonicity |
| A3.5 | Singular covariance handled | test_predictor_math.py | test_singular_covariance_handling |
| A4.1 | Weighted salience formula | test_salience_math.py | test_weighted_formula |
| A4.2 | Neuromodulator modulation | test_salience_math.py | test_neuromodulator_modulation |
| A4.3 | FD energy [0, 1] | test_salience_math.py | test_fd_energy_bounds |
| A4.4 | Soft salience (0, 1) | test_salience_math.py | test_soft_salience_bounds |
| A4.5 | Hysteresis margin | test_salience_math.py | test_hysteresis_margin |
| B1.1 | Evict lowest salience | test_wm_capacity.py | test_evicts_lowest_salience_at_capacity |
| B1.2 | Recency max on admission | test_wm_capacity.py | test_recency_set_on_admission |
| B1.3 | Exponential decay | test_wm_capacity.py | test_recency_decays_exponentially |
| B1.4 | Duplicate update | test_wm_capacity.py | test_duplicate_updates_existing |
| B1.5 | Ranking salience+recency | test_wm_capacity.py | test_ranking_by_salience_recency |
| B2.1 | ANN top-1 identical | test_ltm_search.py | test_ann_returns_top1_for_identical |
| B2.2 | Returns exactly k | test_ltm_search.py | test_returns_exactly_k_items |
| B2.3 | Threshold excludes | test_ltm_search.py | test_threshold_excludes_below |
| B2.4 | Recall@10 > 0.95 | test_ltm_search.py | test_recall_at_10_above_95 |
| B2.5 | Normalized vectors | test_ltm_search.py | test_vectors_normalized_before_storage |
| B3.1 | Payload roundtrip | test_roundtrip.py | test_payload_survives_roundtrip |
| B3.2 | Coordinate deterministic | test_roundtrip.py | test_coordinate_deterministic |
| B3.3 | JSON exact | test_roundtrip.py | test_json_fields_exact |
| B3.4 | Timestamp ms precision | test_roundtrip.py | test_timestamp_millisecond_precision |
| B3.5 | Metadata preserved | test_roundtrip.py | test_metadata_preserved |
| B4.1 | Merge no duplicates | test_fusion.py | test_wm_ltm_merge_no_duplicates |
| B4.2 | Fusion weights | test_fusion.py | test_fusion_weights_applied |
| B4.3 | One source fails | test_fusion.py | test_one_source_fails_returns_other |
| B4.4 | Graph boosts relevance | test_fusion.py | test_graph_retrieval_boosts_relevance |
| B4.5 | Diversity coverage | test_fusion.py | test_diversity_reranking_coverage |
| C1.1 | Dopamine reward | test_neuromodulators.py | test_dopamine_increases_reward_sensitivity |
| C1.2 | Serotonin exploitation | test_neuromodulators.py | test_serotonin_shifts_exploitation |
| C1.3 | Noradrenaline attention | test_neuromodulators.py | test_noradrenaline_narrows_attention |
| C1.4 | Acetylcholine learning | test_neuromodulators.py | test_acetylcholine_increases_learning_rate |
| C1.5 | Values [0, 1] | test_neuromodulators.py | test_all_values_in_valid_range |
| C2.1 | Options by utility | test_planning.py | test_options_ranked_by_utility |
| C2.2 | Context relevance | test_planning.py | test_context_increases_relevance |
| C2.3 | Tie breaking | test_planning.py | test_equal_utility_tie_breaking |
| C2.4 | Timeout best-so-far | test_planning.py | test_timeout_returns_best_so_far |
| C2.5 | No options empty | test_planning.py | test_no_options_returns_empty |
| C3.1 | Positive increases | test_learning.py | test_positive_feedback_increases_weights |
| C3.2 | Negative decreases | test_learning.py | test_negative_feedback_decreases_weights |
| C3.3 | Constraints clamp | test_learning.py | test_constraints_clamp_values |
| C3.4 | Tau annealing | test_learning.py | test_tau_annealing_decay |
| C3.5 | State persists | test_learning.py | test_state_persists_across_restart |
| C4.1 | HRR binding | test_context.py | test_anchors_create_hrr_binding |
| C4.2 | Context decay | test_context.py | test_context_decays_over_time |
| C4.3 | Attention priority | test_context.py | test_attention_prioritizes_retrieval |
| C4.4 | Clear neutral | test_context.py | test_clear_resets_to_neutral |
| C4.5 | Saturation prune | test_context.py | test_saturation_prunes_oldest |
| D1.1 | Tenant A invisible | test_memory_isolation.py | test_tenant_a_invisible_to_tenant_b |
| D1.2 | Cross-tenant empty | test_memory_isolation.py | test_cross_tenant_query_returns_empty |
| D1.3 | Namespace scopes | test_memory_isolation.py | test_namespace_scopes_queries |
| D1.4 | Missing header default | test_memory_isolation.py | test_missing_header_uses_default |
| D1.5 | 100 tenants zero leak | test_memory_isolation.py | test_100_tenants_zero_leakage |
| D2.1 | Neuromodulator isolated | test_state_isolation.py | test_neuromodulator_isolation |
| D2.2 | Circuit breaker isolated | test_state_isolation.py | test_circuit_breaker_isolation |
| D2.3 | Quota isolated | test_state_isolation.py | test_quota_isolation |
| D2.4 | Adaptation isolated | test_state_isolation.py | test_adaptation_isolation |
| D2.5 | WM capacity isolated | test_state_isolation.py | test_wm_capacity_isolation |
| E1.1 | Docker starts all | test_docker_setup.py | test_docker_compose_starts_all_services |
| E1.2 | Redis persistence | test_docker_setup.py | test_redis_accessible_with_persistence |
| E1.3 | Kafka topics | test_docker_setup.py | test_kafka_creates_topics |
| E1.4 | Milvus ready | test_docker_setup.py | test_milvus_ready_for_vectors |
| E1.5 | Postgres migrations | test_docker_setup.py | test_postgres_migrations_apply |
| E2.1 | Health all backends | test_health_verification.py | test_health_includes_all_backends |
| E2.2 | Health degraded | test_health_verification.py | test_health_reports_degraded |
| E2.3 | Prometheus metrics | test_health_verification.py | test_prometheus_metrics_present |
| E2.4 | Jaeger traces | test_health_verification.py | test_jaeger_traces_complete |
| E2.5 | OPA decisions | test_health_verification.py | test_opa_decisions_logged |
| E3.1 | Redis unavailable | test_resilience.py | test_redis_unavailable_degraded_wm |
| E3.2 | Kafka outbox | test_resilience.py | test_kafka_unreachable_outbox_queues |
| E3.3 | Milvus timeout | test_resilience.py | test_milvus_slow_timeout_wm_only |
| E3.4 | Postgres retry | test_resilience.py | test_postgres_retry_exponential_backoff |
| E3.5 | OPA fail-closed | test_resilience.py | test_opa_unavailable_fail_closed |
| F1.1 | Closed to open | test_circuit_state_machine.py | test_closed_to_open_on_threshold |
| F1.2 | Open fails fast | test_circuit_state_machine.py | test_open_fails_fast |
| F1.3 | Open to half-open | test_circuit_state_machine.py | test_open_to_half_open_on_timeout |
| F1.4 | Half-open to closed | test_circuit_state_machine.py | test_half_open_to_closed_on_success |
| F1.5 | Half-open to open | test_circuit_state_machine.py | test_half_open_to_open_on_failure |
| F2.1 | Tenant A independent | test_circuit_per_tenant.py | test_tenant_a_circuit_independent |
| F2.2 | Tenant B unaffected | test_circuit_per_tenant.py | test_tenant_b_unaffected_by_a_open |
| F2.3 | Reset independent | test_circuit_per_tenant.py | test_reset_independent |
| F2.4 | Multiple independent | test_circuit_per_tenant.py | test_multiple_tenants_independent_recovery |
| F2.5 | Metrics by tenant | test_circuit_per_tenant.py | test_metrics_labeled_by_tenant |
| F3.1 | LTM open WM-only | test_degraded_mode.py | test_ltm_open_returns_wm_only_degraded |
| F3.2 | Backend queues outbox | test_degraded_mode.py | test_backend_unavailable_queues_outbox |
| F3.3 | Degraded health | test_degraded_mode.py | test_degraded_health_reports_status |
| F3.4 | Recovery no duplicates | test_degraded_mode.py | test_recovery_replays_without_duplicates |
| F3.5 | Pending zero | test_degraded_mode.py | test_replay_completes_pending_zero |
| G1.1 | Remember p95 < 300ms | test_latency_slo.py | test_remember_p95_under_300ms |
| G1.2 | Recall p95 < 400ms | test_latency_slo.py | test_recall_p95_under_400ms |
| G1.3 | Plan p95 < 1000ms | test_latency_slo.py | test_plan_suggest_p95_under_1000ms |
| G1.4 | Health p99 < 100ms | test_latency_slo.py | test_health_p99_under_100ms |
| G1.5 | Neuro p95 < 50ms | test_latency_slo.py | test_neuromodulators_p95_under_50ms |
| G2.1 | 100 concurrent 99% | test_throughput.py | test_100_concurrent_99_success |
| G2.2 | 1000 memories no loss | test_throughput.py | test_1000_memories_10s_no_loss |
| G2.3 | 500 recalls complete | test_throughput.py | test_500_recalls_10s_complete |
| G2.4 | 30min stable memory | test_throughput.py | test_30min_sustained_stable_memory |
| G2.5 | Spike recovery 30s | test_throughput.py | test_spike_recovery_30s |
| G3.1 | 10K precision@10 | test_recall_quality.py | test_10k_corpus_precision_at_10 |
| G3.2 | 100K recall@10 | test_recall_quality.py | test_100k_corpus_recall_at_10 |
| G3.3 | nDCG@10 > 0.75 | test_recall_quality.py | test_ndcg_at_10_above_75 |
| G3.4 | Diversity < 0.9 | test_recall_quality.py | test_diversity_pairwise_below_90 |
| G3.5 | Freshness recency | test_recall_quality.py | test_freshness_recency_weighted |

---

## Summary

**Total Tasks**: 24 implementation tasks across 8 phases
**Total Test Methods**: 115 acceptance criteria mapped to test methods
**Categories**: 7 (A-G)
**Requirements Covered**: 23

**Execution Order**:
1. Phase 0: Infrastructure setup (3 tasks)
2. Phase 1: Mathematical core - no backend deps (4 tasks)
3. Phase 2: Infrastructure verification (3 tasks)
4. Phase 3: Memory system (4 tasks)
5. Phase 4: Cognitive functions (4 tasks)
6. Phase 5: Multi-tenant isolation (2 tasks)
7. Phase 6: Circuit breaker (3 tasks)
8. Phase 7: Performance (3 tasks)

**Code Quality**: Black, Ruff, Pyright after EVERY task completion.
