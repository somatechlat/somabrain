# Traceability Matrix (ISO/IEC 26512)

**Purpose**: Map features to ISO clauses, documentation pages, and test coverage.

**Last Updated**: 2025-01-27

---

## Feature → Documentation → Tests

| Feature ID | Description | ISO Clause | Doc Page | Test Coverage |
|------------|-------------|------------|----------|---------------|
| F001 | Memory storage (remember) | ISO/IEC 12207§6.4.3 | [Memory Operations](user-manual/features/memory-operations.md) | `tests/integration/test_e2e_memory_http.py` |
| F002 | Memory recall | ISO/IEC 12207§6.4.3 | [Memory Operations](user-manual/features/memory-operations.md) | `tests/integration/test_e2e_memory_http.py` |
| F003 | Batch ingestion | ISO/IEC 12207§6.4.3 | [API Integration](user-manual/features/api-integration.md) | `tests/integration/test_e2e_memory_http.py` |
| F004 | Context evaluation | ISO/IEC 12207§6.4.4 | [Cognitive Reasoning](user-manual/features/cognitive-reasoning.md) | `tests/integration/test_api_diagnostics_and_neuromodulators.py` |
| F005 | Adaptation feedback | ISO/IEC 12207§6.4.4 | [Cognitive Reasoning](user-manual/features/cognitive-reasoning.md) | `tests/workflow/test_adaptation_cycle.py` |
| F006 | Tiered memory | ISO/IEC 12207§6.4.3 | [Architecture](technical-manual/architecture.md) | `tests/core/test_tiered_memory_registry.py` |
| F007 | Circuit breaker | ISO/IEC 12207§6.4.7 | [Architecture](technical-manual/architecture.md) | `tests/services/test_memory_service.py` |
| F008 | Outbox pattern | ISO/IEC 12207§6.4.7 | [Architecture](technical-manual/architecture.md) | `tests/test_admin_outbox.py` |
| F009 | Cutover controller | ISO/IEC 12207§6.4.7 | [Architecture](technical-manual/architecture.md) | `tests/core/test_cutover_controller.py` |
| F010 | Admin endpoints | ISO/IEC 12207§6.4.5 | [API Reference](development-manual/api-reference.md) | `tests/test_admin_features.py` |
| F011 | OPA authorization | ISO/IEC 27001§A.9.4 | [Security](technical-manual/security/rbac-matrix.md) | `tests/cog/test_integrator_opa_policy.py` |
| F012 | Neuromodulators | ISO/IEC 12207§6.4.4 | [Cognitive Reasoning](user-manual/features/cognitive-reasoning.md) | `tests/integration/test_api_diagnostics_and_neuromodulators.py` |
| F013 | Sleep consolidation | ISO/IEC 12207§6.4.4 | [Cognitive Reasoning](user-manual/features/cognitive-reasoning.md) | `tests/integration/test_api_diagnostics_and_neuromodulators.py` |
| F014 | Retrieval pipeline | ISO/IEC 12207§6.4.3 | [Full-Power Recall](technical-manual/full-power-recall.md) | `tests/services/test_retrieval_pipeline.py` |
| F015 | Predictor services | ISO/IEC 12207§6.4.4 | [Predictors](technical-manual/predictors.md) | `tests/services/test_predictor_services.py` |
| F016 | Integrator hub | ISO/IEC 12207§6.4.4 | [Karpathy Architecture](technical-manual/karpathy-architecture.md) | `tests/services/test_integrator_phase2.py` |
| F017 | Segmentation service | ISO/IEC 12207§6.4.4 | [Karpathy Architecture](technical-manual/karpathy-architecture.md) | `tests/services/test_segmentation_phase3.py` |

---

## Test Coverage Summary

| Category | Total Features | Documented | Tested | Coverage % |
|----------|----------------|------------|--------|------------|
| Memory Operations | 3 | 3 | 3 | 100% |
| Cognitive Reasoning | 4 | 4 | 4 | 100% |
| Infrastructure | 4 | 4 | 4 | 100% |
| Admin & Security | 2 | 2 | 2 | 100% |
| Cognitive Threads | 3 | 3 | 3 | 100% |
| **Total** | **17** | **17** | **17** | **100%** |

---

## Verification Process

1. **Feature Implementation** → Code merged to `main`
2. **Documentation** → Feature page created/updated in `docs/`
3. **Test Coverage** → Integration/unit tests added
4. **Traceability** → Entry added to this matrix
5. **Review** → Technical writer + engineer sign-off

---

## Maintenance

- **Quarterly Review**: Verify all features still exist and links are valid
- **On Feature Addition**: Update this matrix before merging
- **On Feature Removal**: Mark as deprecated, archive after 2 releases
