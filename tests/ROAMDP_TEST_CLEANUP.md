# Test Suite Cleanup - ROAMDP Perfection

## Files to Keep (Core Functionality)

### Core Tests (KEEP & MOVE)
- `test_consistency.py` → `tests/core/test_consistency.py`
- `test_bhdc_fusion.py` → `tests/core/test_mathematical_correctness.py`
- `test_roamdp_phase3.py` → `tests/core/test_roamdp_compliance.py`
- `test_sleep_system.py` → `tests/core/test_sleep_system.py`

### E2E Tests (KEEP & MOVE)
- `test_rag_advanced.py` → `tests/e2e/test_rag_workflow.py`
- `test_retrieval_advanced.py` → `tests/e2e/test_retrieval_pipeline.py`

### Performance Tests (KEEP & MOVE)
- `numerics_bench.py` → `tests/performance/test_numerics_performance.py`
- `retrieval_bench.py` → `tests/performance/test_retrieval_performance.py`

## Files to Remove (Legacy/Redundant)

### Benchmarks to Remove
- `test_local_mode.py` - ❌ Local backend deprecated
- `test_redis_mode.py` - ❌ Redis mode removed
- `test_file_outbox.py` - ❌ File-based outbox removed

### Tests to Consolidate
- All BHDC mathematical tests → single `test_mathematical_correctness.py`
- All consistency tests → single `test_consistency.py`

## New Structure

tests/
├── core/
│   ├── test_consistency.py
│   ├── test_mathematical_correctness.py
│   ├── test_roamdp_compliance.py
│   └── test_sleep_system.py
├── e2e/
│   ├── test_rag_workflow.py
│   └── test_retrieval_pipeline.py
├── performance/
│   ├── test_numerics_performance.py
│   └── test_retrieval_performance.py
└── fixtures/
    ├── conftest.py
    └── test_helpers.py