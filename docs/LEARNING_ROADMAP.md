> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain Learning Excellence Roadmap

**Mission**: Transform SomaBrain into the world's best self-learning cognitive system through mathematical rigor, observable adaptation, and production-grade infrastructure.

**Core Principles**:
- **Real Math Only**: No mocks, no bypasses—strict mode everywhere
- **Observable Learning**: Every weight change, every feedback loop visible via metrics
- **Elegant Simplicity**: Clean architecture, minimal complexity, maximum impact
- **Production First**: All features deployed with monitoring, tests, and runbooks

---

## Sprint Overview (2-week cycles)

### **Sprint L1: Observability & Per-Tenant Adaptation** ⚡ IN PROGRESS
**Goal**: Instrument all learning signals and enable independent learning per tenant.

**Deliverables**:
1. **Prometheus Metrics**
   - Gauges for α, β, γ, τ (retrieval weights)
   - Gauges for λ, μ, ν (utility weights)
   - Histogram for feedback latency
   - Counter for feedback applications (success/fail)
   - Gauge for working memory length per tenant
   - Neuromodulator levels (dopamine, serotonin, noradrenaline, acetylcholine)

2. **Per-Tenant Adaptation State**
   - Refactor `AdaptationEngine` to support tenant-scoped instances
   - Persist state snapshots to Redis with tenant prefix
   - Restore state on startup per tenant
   - Add `/context/adaptation/state?tenant_id=X` endpoint

3. **Dynamic Learning Rate**
   - Implement `lr_eff = base_lr * clamp(0.5 + dopamine, 0.5, 1.2)`
   - Wire neuromodulator state into feedback loop
   - Add config toggle `SOMABRAIN_LEARNING_RATE_DYNAMIC=1`

4. **Tau Adaptation**
   - Track repeated memory hits (same coordinate within threshold)
   - Increase τ when diversity drops below target
   - Clamp τ ∈ [0.4, 1.2]
   - Add metric `somabrain_retrieval_tau`

5. **Tests**
   - `tests/test_per_tenant_adaptation.py`: parallel sessions, independent weights
   - `tests/test_dynamic_learning_rate.py`: verify neuromod scaling
   - `tests/test_tau_adaptation.py`: assert diversity maintenance

**Acceptance Criteria**:
- ✅ All metrics exposed at `/metrics` with tenant labels
- ✅ Two tenants can maintain separate adaptation state
- ✅ Dynamic lr scales with dopamine; tests confirm bounds
- ✅ τ increases when same memories repeat; diversity improves
- ✅ State persists across restarts (Redis snapshot/restore)

---

### **Sprint L2: Autonomous Learning Pipeline** ⚡ QUEUED
**Goal**: Activate background learning coordinator to continuously optimize from feedback data.

**Deliverables**:
1. **Background Coordinator**
   - Wire `somabrain/autonomous/coordinator.py` as FastAPI lifespan task
   - Poll `feedback_events` table every 5 minutes
   - Compute performance trends via `FeedbackCollector`
   - Trigger `ParameterOptimizer` when trends detected

2. **Experiment Framework**
   - Define `exp_retrieval_alpha_vs_tau` experiment
   - Implement deterministic group assignment via `assign_to_group`
   - Record results per group in `ExperimentManager`
   - Run Welch's t-test on completion; log p-value and effect size

3. **Canary Promotion**
   - Auto-promote when p < 0.05 and Cohen's d > 0.3
   - Apply winning parameters globally via config update
   - Emit audit event with before/after weights

4. **Graph Augmentation Test**
   - `tests/test_graph_learning.py`: remember → link → recall
   - Assert newly linked nodes appear in subsequent recalls
   - Verify graph_augment_max_additions respected

5. **Tests**
   - `tests/test_autonomous_coordinator.py`: coordinator lifecycle
   - `tests/test_experiment_promotion.py`: canary decision logic
   - Integration test running 100 feedback events → parameter update

**Acceptance Criteria**:
- ✅ Coordinator runs in background without blocking requests
- ✅ Experiment results logged to Postgres and analyzable
- ✅ Winning configurations promoted automatically with audit trail
- ✅ Graph augmentation verified end-to-end

---

### **Sprint L3: Infrastructure & Data Integrity** ⚡ QUEUED
**Goal**: Harden data layer for production scale and ensure zero data loss.

**Deliverables**:
1. **Postgres Optimizations**
   - Add indices: `feedback_events(session_id, created_at)`, `token_usage(session_id)`
   - Implement retention policy: prune feedback > 90 days (cron job)
   - Verify query plans for feedback retrieval < 10ms

2. **Redis Persistence**
   - Enable AOF for working memory and adaptation state
   - Configure save intervals (every 60s if dirty)
   - Test crash recovery with state verification

3. **Kafka Reliability**
   - Update `Docker_Canonical.yml` to KRaft 3-node cluster
   - Configure replication factor = 3 for audit/feedback topics
   - Add health check for broker quorum

4. **Backup & Restore**
   - `scripts/backup_state.sh`: snapshot Redis + Postgres
   - `scripts/restore_state.sh`: restore with validation
   - Document in `docs/DEPLOYMENT_PROD.md`

5. **Tests**
   - `tests/test_persistence_recovery.py`: kill container → restart → verify weights
   - `tests/test_kafka_failover.py`: kill broker → verify audit continues

**Acceptance Criteria**:
- ✅ Postgres queries < 10ms p95 with indices
- ✅ Redis survives container restarts with state intact
- ✅ Kafka audit stream tolerates 1-broker failure
- ✅ Backup/restore tested and documented

---

### **Sprint L4: Enhanced Test Suite** ⚡ QUEUED
**Goal**: Expand coverage to ensure every learning path is validated.

**Deliverables**:
1. **Soak Test Script**
   - `benchmarks/learning_soak.py`: 1k feedback iterations
   - Assert monotonic α/λ growth
   - Track WM length growth rate
   - Verify no weight divergence

2. **Multi-Tenant Stress**
   - Parallel sessions for 10 tenants
   - Each runs 100 feedback loops
   - Assert state isolation (no cross-contamination)

3. **Noise Resilience**
   - Feed random utility values [-1, 1]
   - Verify weights stay bounded
   - Test rollback on extreme outliers

4. **Graph Learning**
   - Create 100 memories with links
   - Recall with graph augment enabled
   - Assert linked nodes appear proportional to weight

5. **CI Integration**
   - Add `pytest -m learning -vv` to GitHub Actions
   - Run soak test nightly on main
   - Block PRs on learning test failures

**Acceptance Criteria**:
- ✅ Soak test runs 1k iterations in < 5 minutes
- ✅ Multi-tenant test shows zero cross-talk
- ✅ Noise test confirms bounded updates
- ✅ Graph test validates link-aware recall
- ✅ CI enforces learning test suite

---

### **Sprint L5: Documentation & Dashboards** ⚡ QUEUED
**Goal**: Make learning observable and tunable for operators.

**Deliverables**:
1. **Learning Tuning Guide**
   - `docs/LEARNING_TUNING.md`: explain α/β/γ/τ/λ/μ/ν
   - Document neuromodulator effects
   - Provide SLO targets and troubleshooting steps

2. **Grafana Dashboards**
   - Adaptation weights panel (time series per tenant)
   - WM growth rate panel
   - Feedback throughput and latency
   - Neuromodulator overlay
   - Experiment results table

3. **Runbook**
   - `docs/ops/LEARNING_RUNBOOK.md`: investigate weight anomalies
   - Query patterns for `feedback_events`
   - Steps to rollback adaptation state
   - Neuromodulator tuning procedure

4. **README Updates**
   - Add learning section with quickstart
   - Link to tuning guide and dashboards
   - Document `/context/adaptation/state` endpoint

**Acceptance Criteria**:
- ✅ Operators can read tuning guide and understand all knobs
- ✅ Dashboards show real-time adaptation for all tenants
- ✅ Runbook validated by simulated incident
- ✅ README directs users to learning resources

---

## Metrics & Success Criteria

### Learning Effectiveness
- **Adaptation Speed**: α increases by ≥0.3 within 20 feedback events
- **Stability**: weights converge within bounds (α ∈ [0.8, 3.0], γ ∈ [0.0, 1.0])
- **Working Memory**: length grows ≥0.5 items per feedback
- **Recall Quality**: Top-1 accuracy improves ≥5% after 100 feedback events

### System Performance
- **Feedback Latency**: p95 < 300ms including Postgres write
- **State Persistence**: restore time < 2s on startup
- **Multi-Tenancy**: 100 concurrent tenants with independent state
- **Experiment Throughput**: analyze 1k results in < 10s

### Observability
- **Metric Coverage**: 100% of adaptation signals exposed
- **Dashboard Latency**: panels update within 5s of event
- **Alert Accuracy**: < 1 false positive per day
- **Audit Completeness**: every parameter change logged

---

## Implementation Strategy

### Parallel Execution (Sprints L1-L3)
Execute L1, L2, L3 in parallel with different team members:
- **L1**: Platform engineer + ML engineer (metrics + adaptation)
- **L2**: Backend engineer (autonomous coordinator)
- **L3**: Infra engineer (Postgres/Redis/Kafka hardening)

### Testing Philosophy
- **Unit tests**: pure functions, mocked dependencies
- **Integration tests**: real Redis/Postgres/Kafka via compose
- **Soak tests**: long-running validation (nightly)
- **Chaos tests**: kill services, verify recovery

### Deployment Cadence
- **Staging**: deploy at end of each sprint
- **Canary**: enable for 10% traffic, monitor 48h
- **Full rollout**: promote if metrics green
- **Rollback**: revert via config toggle + state restore

---

## Risk Mitigation

| Risk | Mitigation | Owner |
|------|-----------|-------|
| Weight divergence | Bounded updates + rollback + alerts | ML Engineer |
| State corruption | Snapshot validation + backup/restore tests | Infra |
| Multi-tenant leak | Isolation tests + namespace prefixing | Backend |
| Performance regression | Soak tests in CI + latency SLOs | Platform |
| Incomplete metrics | Coverage checks + dashboard validation | Observability |

---

## Success Milestones

- **Week 2**: L1 complete, all metrics live, per-tenant state working
- **Week 4**: L2 complete, autonomous coordinator running experiments
- **Week 6**: L3 complete, infrastructure hardened and tested
- **Week 8**: L4 complete, full test suite in CI
- **Week 10**: L5 complete, documentation and dashboards shipped

**Final Validation**: Run production-like load test with 1M feedback events across 100 tenants, verify all SLOs met, zero data loss, complete audit trail.

---

*This roadmap is a living document. Update after each sprint with actual results and lessons learned.*
