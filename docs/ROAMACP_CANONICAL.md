> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

Project Plan – ROAMACP Canonical (Sprint Roadmap)

Purpose
-------
This canonical roadmap lays out a 4‑sprint plan to align the SomaBrain codebase and infra with the consolidated shared‑infra architecture. Each sprint has clear deliverables, acceptance criteria, CI gates, and owners. The goal is to remove stub fallbacks, centralise infra, and enable reliable integration testing using Kind and Helm.

High‑level timeline
-------------------
- Sprint 0 (prep): 1 week — finalize infra component selection and sizing (optionally run in parallel with Sprint 1).
- Sprint 1: 2 weeks — Make `soma-infra` Helm chart deployable locally (dev & Kind) and add CI smoke checks.
- Sprint 2: 2 weeks — Wire settings/Secrets (ConfigMap/Secret and Vault annotations) and add observability provisioning.
- Sprint 3: 2 weeks — App wiring, feature‑flags, and strict‑real enforcement audit + CI Kind integration for full tests.
- Sprint 4: 1–2 weeks — GitOps, docs, runbooks and final verification / release.

Sprint details
--------------

Sprint 0 (Prep, 1 week)
- Goal: Lock infra component versions and naming conventions; prepare values files and sizing.
- Deliverables:
	- `infra/helm/charts/soma-infra/README.md` with selected charts and versions (Kafka operator, Redis chart, Vault, Prometheus-operator, Grafana provisioning approach).
	- `infra/helm/values-{dev,staging,prod}.yaml` templates (dev already has `values-dev.yaml`).
- Acceptance criteria:
	- README reviewed and agreed by infra owner.
	- Values templates cover env differences (dev vs prod).

Sprint 1 (2 weeks)
- Goal: Make `soma-infra` deployable and testable locally and in CI (Kind). Provide simple developer flow.
- Deliverables:
	- Fully rendered `infra/helm/charts/soma-infra` with Helm dependencies or embedded subcharts for: Auth, OPA, Kafka (or Redpanda), Redis, Prometheus, Grafana, Vault, Etcd.
	- Templates: `templates/configmap.yaml`, `templates/secret.yaml`, and `templates/deployment-labels.yaml` (propagate `configHash`).
	- Developer scripts: `scripts/infra_kind_up.sh` (create kind cluster, add registry, install infra) and `scripts/start_dev_infra.sh` (docker-compose path retained for quick iteration).
	- CI job skeleton: `ci/integration-kind.yml` (or additions to `.github/workflows/ci.yml`) which installs Helm and the infra into Kind and runs smoke checks.
- Acceptance criteria:
	- `scripts/infra_kind_up.sh` can install the infra chart into a local Kind cluster and smoke endpoints (Auth/OPA/Redis) return healthy.
	- CI Kind job completes install + smoke checks in < 20 minutes for PRs (can be a gated optional job initially).

Sprint 2 (2 weeks)
- Goal: Wire configuration & secrets and observability.
- Deliverables:
	- Helm templates for ConfigMap/Secret generation from `values.yaml` and `templates` annotations for Vault agent injection.
	- Prometheus + Grafana provisioning (ConfigMap dashboards) and `infra/helm/grafana/dashboards/` with at least one dashboard for core services.
	- `common/utils/otel_instrumentation.py` scaffolding and example instrumentation in one app (e.g., `sb`).
- Acceptance criteria:
	- Deploy infra + `sb` into Kind, confirm that Prometheus scrapes `/metrics` and Grafana imports the dashboard via provisioning.
	- Vault agent annotation demonstrates secret injection with a test secret in dev (or emulated via Kubernetes Secret for dev).

Sprint 3 (2 weeks)
- Goal: App wiring, feature flags, and strict‑real policy enforcement across the codebase.
- Deliverables:
	- `common/feature_flags.py` with Etcd client + Redis caching + Kafka topic invalidation scaffold, and unit tests.
	- Audit report listing every remaining stub/fallback occurrence (grep for `record_stub`, `_GLOBAL_PAYLOADS`, `mirror_append`, `in_process_stub`) and PRs to remove them (or convert to explicit errors under `SOMABRAIN_STRICT_REAL`).
	- CI Kind integration runs full integration tests with `SOMABRAIN_STRICT_REAL=1` and fails if services missing or stubs used.
- Acceptance criteria:
	- Feature flags tested: update a flag in Etcd (or simulated) and observe cache invalidation via Kafka topic processing.
	- All stub fallbacks removed or converted; unit and integration tests pass with strict-real enabled.

Sprint 4 (1–2 weeks)
- Goal: Finalise GitOps, docs, and cut the release.
- Deliverables:
	- ArgoCD application manifests (`infra/argocd/`) and example app declarations for `soma-infra` and `sb`.
	- `docs/runbook.md` and `docs/architecture.md` updated with how to run infra locally, test guidelines (`DISABLE_START_SERVER`, `SOMABRAIN_STRICT_REAL`), and DR checklists.
	- Final PR merging `soma_integration` into `main` with all CI passing and release notes.
- Acceptance criteria:
	- ArgoCD can sync the `infra/helm` chart into a cluster (manual or test cluster).
	- The runbook is clear and verified by following it to deploy infra+app and run smoke tests.

Cross‑cutting acceptance & CI gates
----------------------------------
- Unit tests: All unit tests must pass in the `test` job. We already relaxed pytest selection to enable that.
- Integration smoke: For PRs we run a fast smoke check using either docker-compose or a Kind job (choose one). Longer full integration runs may execute on schedule or on release branches.
- Strict‑real gate: The full integration job (Kind) runs with `SOMABRAIN_STRICT_REAL=1` and fails if any stub fallback is used or required infra endpoints are unreachable.

Minimal milestones (first 7 days)
---------------------------------
1. Finalize infra chart README and component versions (Sprint 0 deliverable).
2. Add Helm templates for `ConfigMap` and `Secret` and `deployment-labels.yaml` into `soma-infra` (Sprint 1 subset).
3. Add `scripts/infra_kind_up.sh` and a CI job skeleton for installing the infra into Kind (Sprint 1 subset).

Who does what (roles suggested)
------------------------------
- Infra owner: helm chart assembly, Kind CI job, resource sizing.
- Platform owner: Vault integration, ArgoCD manifests, GitOps onboarding.
- App owners: migrate service settings to use `common/config/settings.py`, add OTEL instrumentation, remove stub fallbacks.
- QA/Tester: write integration tests, maintain `tests/integration/` and smoke harness.

Risks and mitigations
---------------------
- Kafka/Stateful services in Kind may be slow or flaky.
	- Mitigation: prefer lightweight Redpanda for dev, use docker-compose for local iteration and Kind for CI smoke only.
- Vault in dev is heavy.
	- Mitigation: emulate secrets with Kubernetes `Secret` in dev; enable Vault for staging/prod.

Next immediate steps I will take if you confirm
----------------------------------------------
1. Create the expanded `infra/helm/charts/soma-infra/templates/` stubs: `configmap.yaml`, `secret.yaml`, `deployment-labels.yaml` and a `README.md` describing dependencies and dev install steps. (Sprint 1 — minimal subset)
2. Add a Kind CI job skeleton to `.github/workflows/ci.yml` named `integration-kind` that creates a kind cluster, installs Helm, deploys `soma-infra`, and runs a few smoke checks. (Sprint 1 — minimal subset)

If you want me to start now, say "Start Sprint 1 subset" and I'll create the three Helm template files plus the Kind CI job skeleton and push the changes to the branch.

Canonical roadmap saved.

