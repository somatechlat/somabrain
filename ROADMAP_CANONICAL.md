# Canonical Cognitive-Thread Roadmap

## Overview
This roadmap delivers a production-grade cognitive-thread pipeline with:
- Four new microservices: predictor_state, predictor_agent, predictor_action, segmentation_service, integrator_hub
- OPA sidecar for policy gating
- Avro schemas, config centralization, robust CI/CD, and full observability
- Feature-flag controlled rollout and instant rollback

## Sprints & Deliverables

### Sprint 0: Foundations
- Validate Avro schemas, config files, and CI pipeline
- Document all feature flags and config options

### Sprint 1: Predictors
- Implement Dockerfiles, API docs, and metrics for predictor services
- End-to-end test: `/predict` → Kafka topic Avro record

### Sprint 2: Segmentation
- Validate segmentation service logic, metrics, and probes
- Test BOCPD hazard and segment event emission

### Sprint 3: Integrator Hub
- Implement leader election, OPA integration, Redis caching, and metrics
- Test policy rejections and global frame publication

### Sprint 4: OPA Policies
- Version and test Rego policies
- Validate sidecar deployment and API contract

### Sprint 5: Observability & Helm
- Add dashboards, update Helm chart for probes/limits
- Test feature flag toggling and metrics exposure

### Sprint 6: Canary & Production
- Automate canary rollout, run load tests, monitor latency and I/O
- Validate rollback plan and instant legacy path recovery

## Checklist
- All logic is config-driven; no hard-coded thresholds
- Mathematical core (Δerror, salience, softmax, HMM/BOCPD) is implemented and tested
- Security and observability meet VIBE standards
- CI/CD and test suite ensure functional correctness
- Feature-flag guarantees backward compatibility

## Rollback Plan
Set `featureFlags.enableCogThreads` to `false` in Helm values and run `helm upgrade` to instantly revert to legacy path.

---

This roadmap replaces all previous content and is the canonical plan for cognitive-thread production rollout.
