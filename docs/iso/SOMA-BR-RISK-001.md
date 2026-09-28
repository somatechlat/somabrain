# SOMA-BR-RISK-001: SomaBrain Risk Register

> **Standard:** ISO 31000:2018 — Risk Management — Guidelines
> **Owner:** SomaTech Risk Management

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Risk Register |
| Document Identifier | SOMA-BR-RISK-001 |
| Version | 2.0.1 |
| Date | 2026-06-15 |
| Status | Approved |
| Author | SomaTech Risk Management |
| Approver | VP Engineering, SomaTech |
| Classification | Internal |
| ISO Reference | ISO 31000:2018 — Risk Management — Guidelines |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-02-01 | Risk Management | Initial risk register |
| 1.5.0 | 2026-04-15 | Risk Management | Added dependency and scaling risks |
| 2.0.0 | 2026-06-15 | Risk Management | Comprehensive update: all five primary risks with quantitative analysis |
| 2.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-BR-RISK-001` \| Status added as `Approved` (document names an approver). |

---

## Table of Contents

1. [Risk Management Framework](#1-risk-management-framework)
2. [Risk Assessment Matrix](#2-risk-assessment-matrix)
3. [Risk R-001: Complexity Debt](#3-risk-r-001-complexity-debt)
4. [Risk R-002: SomaFractalMemory Dependency](#4-risk-r-002-somafractalmemory-dependency)
5. [Risk R-003: Kafka Availability](#5-risk-r-003-kafka-availability)
6. [Risk R-004: Milvus Scaling](#6-risk-r-004-milvus-scaling)
7. [Risk R-005: Neuromodulator Calibration Drift](#7-risk-r-005-neuromodulator-calibration-drift)
8. [Secondary Risks](#8-secondary-risks)
9. [Risk Treatment Plan Summary](#9-risk-treatment-plan-summary)
10. [Risk Monitoring](#10-risk-monitoring)

---

## 1. Risk Management Framework

### 1.1 Methodology

This risk register follows ISO 31000:2018 principles:

- **Identification:** Systematic identification of threats to system reliability, security, and performance
- **Analysis:** Likelihood × Impact scoring with quantitative estimates where possible
- **Evaluation:** Prioritization against risk appetite thresholds
- **Treatment:** Mitigation strategies with owners and timelines
- **Monitoring:** Quarterly review cycle with trigger-based escalation

### 1.2 Scoring

**Likelihood Scale:**

| Score | Likelihood | Description |
|---|---|---|
| 1 | Rare | < 10% probability in next 12 months |
| 2 | Unlikely | 10-30% probability |
| 3 | Possible | 30-50% probability |
| 4 | Likely | 50-75% probability |
| 5 | Almost Certain | > 75% probability |

**Impact Scale:**

| Score | Impact | Description |
|---|---|---|
| 1 | Negligible | < 1 hour degradation, no data impact |
| 2 | Minor | 1-4 hours degradation, limited scope |
| 3 | Moderate | 4-24 hours degradation, significant scope |
| 4 | Major | > 24 hours degradation, widespread impact |
| 5 | Critical | Data loss, security breach, or extended outage |

**Risk Score:** Likelihood × Impact (1-25)

| Risk Score | Level | Response |
|---|---|---|
| 1-4 | Low | Accept and monitor |
| 5-9 | Medium | Mitigate with standard controls |
| 10-15 | High | Priority mitigation required |
| 16-25 | Critical | Immediate escalation and action |

---

## 2. Risk Assessment Matrix

| Risk ID | Risk | Likelihood | Impact | Score | Level | Owner |
|---|---|---|---|---|---|---|
| R-001 | Complexity Debt (116K LOC) | 4 | 3 | **12** | High | Architecture Team |
| R-002 | SomaFractalMemory Dependency | 3 | 4 | **12** | High | Operations Team |
| R-003 | Kafka Availability | 3 | 3 | **9** | Medium | Infrastructure Team |
| R-004 | Milvus Scaling | 3 | 4 | **12** | High | Infrastructure Team |
| R-005 | Neuromodulator Calibration Drift | 4 | 2 | **8** | Medium | Cognitive Team |

### Risk Heat Map

```
Impact
  5 │           │           │           │           │
  4 │           │           │  R-002    │           │
  3 │           │  R-003    │ R-004     │ R-001     │
  2 │           │  R-005    │           │           │
  1 │           │           │           │           │
    └───────────┴───────────┴───────────┴───────────┘
         1           2           3           4          5
                        Likelihood
```

---

## 3. Risk R-001: Complexity Debt

### 3.1 Description

**The 116,735-line Python codebase creates significant cognitive load** for developers, reviewers, and new team members. As the codebase grows organically, the risk of subtle bugs in under-reviewed areas, inconsistent patterns, and delayed feature delivery increases.

### 3.2 Assessment

| Attribute | Value |
|---|---|
| Likelihood | 4 (Likely) — complexity debt is actively accumulating |
| Impact | 3 (Moderate) — reduced velocity, increased defect rate |
| Risk Score | 12 (High) |
| Risk Owner | Architecture Team |

### 3.3 Contributing Factors

| Factor | Severity | Description |
|---|---|---|
| Codebase size | High | 116,735 Python LOC — exceeds comfortable single-team maintenance |
| Module count | Medium | 50+ modules with varying cohesion |
| Configuration surface | Medium | 300+ tunable parameters |
| Domain complexity | Medium | Cognitive science + HDC + distributed systems |
| Onboarding time | High | Estimated 3-6 months for full productivity |

### 3.4 Existing Mitigations

| Mitigation | Status | Effectiveness |
|---|---|---|
| Architecture document (SOMA-BR-ARCH-001) | ✅ Active | High — provides structural navigation |
| Brain-region module metaphor | ✅ Active | Medium — intuitive but not formal |
| Cognitive presets (Stable/Plastic/Lateral) | ✅ Active | Medium — reduces parameter surface |
| 95 test files | ✅ Active | High — regression detection |
| Zero TODO/FIXME discipline | ✅ Active | Medium — prevents deferred debt |
| VIBE coding rules | ✅ Active | Low — enforcement mechanism unclear |

### 3.5 Treatment Plan

| Action | Owner | Timeline | Priority |
|---|---|---|---|
| Create module-level architecture diagrams for top-20 modules | Architecture Team | 2026-09-15 | High |
| Implement automated API docs (Sphinx/MkDocs) | DevOps | 2026-08-15 | High |
| Establish module ownership model | Engineering Leads | 2026-08-01 | High |
| Add code complexity metrics to CI (cyclomatic complexity) | DevOps | 2026-09-01 | Medium |
| Plan incremental refactoring sprints (1 per quarter) | Architecture Team | Ongoing | Medium |

### 3.6 Triggers for Escalation

- Onboarding time exceeds 6 months for new developers
- Defect rate increases by > 25% quarter-over-quarter
- Feature delivery velocity drops by > 30%

---

## 4. Risk R-002: SomaFractalMemory Dependency

### 4.1 Description

**SomaBrain's AAAS mode depends on SomaFractalMemory (port 63901) for distributed long-term memory persistence.** If SomaFractalMemory becomes unavailable or degraded, SomaBrain cannot persist consolidated memories or serve cross-agent memory queries.

### 4.2 Assessment

| Attribute | Value |
|---|---|
| Likelihood | 3 (Possible) — external dependency with its own failure modes |
| Impact | 4 (Major) — long-term memory unavailable; working memory unaffected |
| Risk Score | 12 (High) |
| Risk Owner | Operations Team |

### 4.3 Failure Modes

| Mode | Symptom | Impact on SomaBrain |
|---|---|---|
| Complete outage | HTTP connection refused | Consolidation blocked; recall degraded to local sources |
| Partial degradation | Elevated latency (> 500ms) | Consolidation slowed; recall timeout risk |
| Data corruption | Invalid responses | Constitution signing catches; data rejected |
| Split-brain | Inconsistent state | Provenance chain detects divergence |

### 4.4 Existing Mitigations

| Mitigation | Status | Effectiveness |
|---|---|---|
| Graceful degradation to local memory | ✅ Active | High — WM and LTM still functional |
| HTTP timeout + retry with backoff | ✅ Active | Medium — prevents cascading timeout |
| Constitution signing verification | ✅ Active | High — rejects corrupted data |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` configurable | ✅ Active | Medium — allows endpoint switching |
| Optional direct Python import | ✅ Active | Low — bypasses HTTP but tightens coupling |

### 4.5 Treatment Plan

| Action | Owner | Timeline | Priority |
|---|---|---|---|
| Implement circuit breaker for SFM HTTP client | Operations Team | 2026-08-15 | High |
| Add SFM health check to SomaBrain's readiness probe | DevOps | 2026-08-01 | High |
| Implement local write-ahead log for deferred SFM writes | Architecture Team | 2026-09-15 | Medium |
| Negotiate SLA with SomaFractalMemory team | Operations Team | 2026-08-01 | Medium |
| Add SFM availability to Prometheus dashboards | DevOps | 2026-08-01 | Low |

### 4.6 Triggers for Escalation

- SomaFractalMemory downtime exceeds 30 minutes
- Data integrity errors detected by constitution signing
- SFM latency exceeds 500ms p95 for > 5 minutes

---

## 5. Risk R-003: Kafka Availability

### 5.1 Description

**SomaBrain uses Kafka for the cognitive event pipeline (5 topics, 17 Avro schemas).** Kafka unavailability disrupts the cognitive pipeline flow, preventing event-driven processing between predictors, integrator, and memory store.

### 5.2 Assessment

| Attribute | Value |
|---|---|
| Likelihood | 3 (Possible) — Kafka is a complex distributed system |
| Impact | 3 (Moderate) — pipeline stalled; direct-call fallback exists for some operations |
| Risk Score | 9 (Medium) |
| Risk Owner | Infrastructure Team |

### 5.3 Affected Topics

| Topic | Criticality | Fallback |
|---|---|---|
| `cog.perceive` | High | Direct API call bypasses Kafka |
| `cog.predict` | Medium | Predictor can run synchronously |
| `cog.integrate` | High | Integrator can run synchronously |
| `cog.segment` | Medium | Segmenter can run inline |
| `cog.store` | High | Transactional outbox enables replay |

### 5.4 Existing Mitigations

| Mitigation | Status | Effectiveness |
|---|---|---|
| Transactional outbox pattern | ✅ Active | High — events replayable after Kafka recovery |
| Kafka health check in readiness probe | ✅ Active | Medium — detects outage early |
| Prometheus Kafka lag metrics | ✅ Active | Medium — alerts on consumer lag |
| Schema registry for schema evolution | ✅ Active | Medium — prevents schema conflicts |
| Synchronous fallback paths | ⚠️ Partial | Low — not all services have fallback |

### 5.5 Treatment Plan

| Action | Owner | Timeline | Priority |
|---|---|---|---|
| Validate synchronous fallback for all 5 topics | Architecture Team | 2026-09-01 | High |
| Add Kafka consumer lag alerting (PagerDuty integration) | DevOps | 2026-08-15 | Medium |
| Implement dead-letter queue for failed messages | Infrastructure Team | 2026-09-15 | Medium |
| Test Kafka broker failure under load | QA Team | 2026-10-01 | Medium |

### 5.6 Triggers for Escalation

- Kafka broker quorum lost
- Consumer lag exceeds 10,000 messages
- Outbox replay backlog exceeds 1 hour

---

## 6. Risk R-004: Milvus Scaling

### 6.1 Description

**SomaBrain uses Milvus for vector similarity search (HNSW index).** As memory volume grows, Milvus may face scaling challenges including index build time, query latency, and memory consumption.

### 6.2 Assessment

| Attribute | Value |
|---|---|
| Likelihood | 3 (Possible) — scaling challenges emerge at scale |
| Impact | 4 (Major) — recall latency and availability affected |
| Risk Score | 12 (High) |
| Risk Owner | Infrastructure Team |

### 6.3 Scaling Dimensions

| Dimension | Current | Projected (12mo) | Risk |
|---|---|---|---|
| Memory count | 12M | 100M+ | Index build time, storage |
| Vector dimension | 8,192 | 8,192 | Memory per vector |
| Query QPS | 5,000/s | 20,000/s | Query latency |
| Tenants (AAAS) | ~10 | ~100 | Collection count, resource isolation |

### 6.4 Existing Mitigations

| Mitigation | Status | Effectiveness |
|---|---|---|
| HNSW index (efficient approximate search) | ✅ Active | High — sub-linear query time |
| Per-tenant Milvus collections | ✅ Active | Medium — isolation but collection proliferation |
| Milvus query duration Prometheus metrics | ✅ Active | Medium — monitoring in place |
| Batch insert for consolidation | ✅ Active | Medium — reduces index rebuild frequency |

### 6.5 Treatment Plan

| Action | Owner | Timeline | Priority |
|---|---|---|---|
| Benchmark Milvus at 100M vectors | Infrastructure Team | 2026-09-01 | High |
| Evaluate Milvus partition strategies for multi-tenancy | Architecture Team | 2026-09-15 | High |
| Implement Milvus cluster mode for AAAS | Infrastructure Team | 2026-10-01 | Medium |
| Add Milvus index build time monitoring | DevOps | 2026-08-15 | Medium |
| Evaluate alternative vector stores (Qdrant, Weaviate) as contingency | Architecture Team | 2026-12-01 | Low |

### 6.6 Triggers for Escalation

- Milvus query latency p95 exceeds 100ms
- Index build time exceeds 30 minutes
- Milvus memory consumption exceeds 80% of available RAM

---

## 7. Risk R-005: Neuromodulator Calibration Drift

### 7.1 Description

**SomaBrain simulates neuromodulators (dopamine, serotonin, norepinephrine, acetylcholine) that modulate cognitive parameters.** Over time, the calibration of these neuromodulators may drift from optimal values, leading to degraded memory quality (excessive plasticity, poor recall precision, or stale memory states).

### 7.2 Assessment

| Attribute | Value |
|---|---|
| Likelihood | 4 (Likely) — drift is a natural consequence of non-stationary inputs |
| Impact | 2 (Minor) — degraded quality, not service failure |
| Risk Score | 8 (Medium) |
| Risk Owner | Cognitive Team |

### 7.3 Drift Manifestations

| Modulator | Drift Direction | Symptom |
|---|---|---|
| Dopamine | Too high | Excessive plasticity; noisy memory storage |
| Dopamine | Too low | Insufficient learning; stale memories |
| Serotonin | Too high | Over-stabilization; resistance to new information |
| Serotonin | Too low | Mood instability in agent behavior |
| Norepinephrine | Too high | Hypervigilance; excessive surprise signals |
| Norepinephrine | Too low | Missed anomalies; low alertness |
| Acetylcholine | Too high | Over-attending to irrelevant stimuli |
| Acetylcholine | Too low | Poor attention; weak learning signal |

### 7.4 Existing Mitigations

| Mitigation | Status | Effectiveness |
|---|---|---|
| Calibration service (`calibration_service.py`) | ✅ Active | Medium — monitors and adjusts levels |
| Cognitive presets (bounded parameter ranges) | ✅ Active | Medium — prevents extreme drift |
| Prometheus neuromodulator metrics | ✅ Active | Medium — monitoring in place |
| Adaptive plasticity gain (GMD η modulation) | ✅ Active | Medium — self-correcting mechanism |
| Parameter Supervisor | ✅ Active | Medium — preset-based governance |

### 7.5 Treatment Plan

| Action | Owner | Timeline | Priority |
|---|---|---|---|
| Implement automated drift detection alerts | Cognitive Team | 2026-09-01 | Medium |
| Add A/B testing framework for calibration parameters | Cognitive Team | 2026-10-01 | Medium |
| Implement calibration reset mechanism (manual trigger) | Cognitive Team | 2026-08-15 | Medium |
| Add memory quality metrics (precision, recall, freshness) | Cognitive Team | 2026-09-15 | Medium |
| Research optimal calibration bounds from literature | Research Team | 2026-12-01 | Low |

### 7.6 Triggers for Escalation

- Memory recall precision drops by > 15% from baseline
- Neuromodulator levels exceed preset bounds for > 1 hour
- Agent behavior anomalies reported by SomaAgent01

---

## 8. Secondary Risks

| Risk ID | Risk | Likelihood | Impact | Score | Level | Notes |
|---|---|---|---|---|---|---|
| R-006 | PostgreSQL single point of failure | 2 | 4 | 8 | Medium | Mitigated by replication in production |
| R-007 | Redis cache stampede on cold start | 3 | 2 | 6 | Medium | Mitigated by warm-up scripts |
| R-008 | Rust core compilation failures | 2 | 2 | 4 | Low | Pure Python fallback exists |
| R-009 | Configuration sprawl (300+ params) | 4 | 2 | 8 | Medium | Mitigated by cognitive presets |
| R-010 | Supply chain vulnerability | 3 | 3 | 9 | Medium | No automated scanning in CI yet |
| R-011 | Key staff dependency | 3 | 3 | 9 | Medium | 116K LOC + cognitive science expertise |
| R-012 | VIBE rules drift without enforcement | 4 | 2 | 8 | Medium | Convention-based enforcement |

---

## 9. Risk Treatment Plan Summary

### 9.1 By Priority

| Priority | Count | Total Risk Score Reduction |
|---|---|---|
| High | 8 actions | Est. -35 points |
| Medium | 15 actions | Est. -25 points |
| Low | 5 actions | Est. -8 points |

### 9.2 Resource Requirements

| Area | Effort (person-weeks) | Timeline |
|---|---|---|
| Architecture diagrams + documentation | 4 | 2026-08 to 2026-09 |
| Infrastructure hardening (Kafka, Milvus, SFM) | 6 | 2026-08 to 2026-10 |
| Cognitive calibration improvement | 3 | 2026-08 to 2026-12 |
| DevOps and monitoring | 3 | 2026-08 to 2026-09 |
| **Total** | **16** | **2026-08 to 2026-12** |

---

## 10. Risk Monitoring

### 10.1 Review Cadence

| Review Type | Frequency | Participants |
|---|---|---|
| Risk register review | Quarterly | Architecture, Ops, Cognitive teams |
| Trigger-based escalation | As needed | Risk owner + VP Engineering |
| Annual risk assessment | Annually | Full engineering team |

### 10.2 Key Risk Indicators (KRIs)

| KRI | Threshold | Monitoring |
|---|---|---|
| Defect rate | > 25% increase QoQ | Issue tracker metrics |
| Onboarding time | > 6 months | Team lead feedback |
| SomaFractalMemory downtime | > 30 min | Prometheus + alerting |
| Kafka consumer lag | > 10,000 messages | Prometheus Kafka exporter |
| Milvus query latency p95 | > 100ms | Prometheus Milvus metrics |
| Neuromodulator out-of-bounds | > 1 hour | Prometheus + calibration service |
| Memory recall precision | > 15% drop | Cognitive quality metrics |

### 10.3 Dashboard

Risk metrics are aggregated on the SomaTech risk dashboard (Grafana) with automated alerting to PagerDuty for High and Critical risk triggers.

---

*End of register. This risk management framework follows ISO 31000:2018 principles and is subject to quarterly review.*
