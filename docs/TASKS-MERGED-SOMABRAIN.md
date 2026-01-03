# SomaBrain — Merged Tasks & Requirements

**Document:** TASKS-MERGED-SOMABRAIN.md  
**Version:** 1.0.0  
**Date:** 2026-01-03  
**Source:** Merged from SRS-SOMABRAIN-MASTER.md and AGENT.md

---

## Quick Reference

| Metric | Value |
|--------|-------|
| Total Files | 377 |
| VIBE Compliance | 99.8% |
| Outstanding TODOs | 1 |
| Action Items | 1 |

---

## 1. Core Cognitive Tasks

### 1.1 Brain Region Modules (Status: ✅ Complete)
| Module | Lines | Status |
|--------|-------|--------|
| neuromodulators.py | 334 | ✅ |
| wm.py (Working Memory) | 546 | ✅ |
| hippocampus.py | 112 | ✅ |
| amygdala.py | 260 | ✅ |
| prefrontal.py | 108 | ✅ |
| thalamus.py | 86 | ✅ |
| consolidation.py | 203 | ✅ |

### 1.2 Mathematical Foundations (Status: ✅ Complete)
| Module | Lines | Status |
|--------|-------|--------|
| quantum_pure.py (HRR) | 159 | ✅ |
| math/similarity.py | 183 | ✅ |
| sdr.py | 252 | ✅ |
| math/lanczos_chebyshev.py | 158 | ✅ |

---

## 2. Outstanding Tasks (P1)

### 2.1 Rate Limiting (From SRS-SOMABRAIN-MASTER)
| Task | Location | Effort | Status |
|------|----------|--------|--------|
| Implement rate limiting | `api/endpoints/auth.py:134` | 0.5d | ❌ TODO |

### 2.2 Capsule Integration
| Task | Effort | Status |
|------|--------|--------|
| Accept Capsule identity push from SomaAgent01 | 0.5d | ⚠️ Partial |
| Apply neuromodulator_baseline from Capsule | 0.5d | ⚠️ |
| Apply personality_traits from Capsule | 0.5d | ⚠️ |

---

## 3. Integration Tasks

### 3.1 SomaFractalMemory Integration
| Task | Effort | Status |
|------|--------|--------|
| Memory HTTP client stable | 0d | ✅ |
| Store/Recall endpoints tested | 0d | ✅ |
| Fallback on memory unavailable | 0.5d | ⚠️ |

### 3.2 SomaAgent01 Integration
| Task | Effort | Status |
|------|--------|--------|
| Accept system_prompt injection | 0d | ✅ |
| Return streaming SSE responses | 0d | ✅ |
| Capsule verification callback | 1d | ❌ |

---

## 4. Observability Tasks

| Task | Effort | Status |
|------|--------|--------|
| Prometheus metrics for cognitive_loop | 0.5d | ⚠️ Partial |
| Neuromodulator level gauges | 0.5d | ❌ |
| Working memory capacity gauge | 0.25d | ❌ |
| Consolidation cycle counter | 0.25d | ❌ |

---

## 5. Test Coverage

| Area | Coverage | Action |
|------|----------|--------|
| Brain regions | 80% | Increase to 90% |
| Math modules | 95% | ✅ OK |
| API endpoints | 70% | Add rate limit tests |
| Integration | 60% | Add Capsule push tests |

---

## 6. Implementation Phases

### Phase 1: Rate Limiting (Week 1)
- [ ] Implement rate limiting in `auth.py`
- [ ] Add Redis-based token bucket

### Phase 2: Capsule Integration (Week 1-2)
- [ ] Apply Capsule personality to cognitive loop
- [ ] Add verification callback to Agent01

### Phase 3: Observability (Week 2)
- [ ] Complete Prometheus metrics
- [ ] Add Grafana dashboard

---

## 7. Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `api/endpoints/auth.py` | MODIFY | Add rate limiting |
| `services/cognitive_loop_service.py` | MODIFY | Accept Capsule traits |
| `services/integrator_hub_triplet.py` | VERIFY | Capsule personality |
| `metrics/exporters.py` | MODIFY | Add cognitive metrics |

---

**Total Effort Estimate:** 3-4 developer days

---

*END OF MERGED TASKS — SOMABRAIN*
