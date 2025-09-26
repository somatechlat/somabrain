# SomaBrain Detailed Architecture

This document captures the fine-grained architecture required to deliver a
production-grade SomaBrain capable of handling millions of agent transactions per day. It expands on
module responsibilities, service dependencies, scaling strategies, and data flows.

## 1. Service Topology

### 1.1 Control Plane
- **Envoy Ingress** – terminates mTLS, enforces WAF/rate limits, authenticates JWT/OIDC tokens.
- **Brain API (FastAPI/uvicorn)** – primary entry point; exposes REST/gRPC endpoints for agent
  requests, memory operations, and health checks. Auto-discovers host ports via `scripts/dev_up.sh`
  during local deploys and via config maps in production.
- **Context/Planner Service** – `somabrain/context` + `somabrain/planner` coordinate the abstracted
  LLM/SLM behaviours (multi-view retrieval, HRR compression, hill-climb reasoning). The API returns
  structured `ContextBundle` payloads for agents to feed into their SLM stack.
- **OPA Policy Pods** – enforce Rego policies derived from the constitution. Deployed as sidecars or
  a pooled service, with bundle distribution and hot reload.
- **Constitution Engine** – `somabrain/constitution/cloud.py` orchestrates reads/writes to managed
  Redis (primary), Postgres (history), and object storage (immutable snapshots). Threshold signature
  verification happens here.

### 1.2 Data & Messaging Plane
- **Kafka/KRaft Cluster** – 3–5 brokers, TLS/SASL enabled. Topics:
  - `soma.audit` (immutable, replicate=3)
  - `soma.constitution.revisions` (immutable)
  - `soma.memory.events` (source-of-truth for memory operations)
  - `soma.telemetry` (high-volume metrics/trace exports)
- **Redis Cluster** – in-memory cache for constitution hot copy, hot memories, rate limiting, and
  audit buffer.
- **Postgres HA** – stores constitution metadata, token ledgers, tenant config, reward records, graph
  adjacency, and time-series metrics (Timescale extension).
- **Vector Store (Qdrant or PGVector)** – sharded, replicated vector search for memory embeddings.
- **Object Storage (S3/GCS)** – stores signed constitution snapshots, audit archives, benchmark
  outputs, and release artefacts.

### 1.3 Compute & Memory Pipeline
- **Agent SLM clients (external)** – agents (and test harnesses) run their own SLM inference
  stacks. SomaBrain prepares the governed context bundles and metrics those agents need. The
  repository retains lightweight client shims and contract tests but does not run inference
  workloads itself.
- **Memory Integrity Worker** – background service consuming `soma.memory.events`, verifying that
  Redis/Qdrant/Postgres remain in sync.
- **Reward Gate Worker** – Kafka consumer that correlates audit outcomes with agent reward signals.
- **Benchmark & Chaos Runners** – scheduled workloads that stress-test throughput and failure modes.
- **Working Memory Cache** – Redis-backed ring buffer retaining per-conversation scratchpads so the
  agent receives a bounded "residual stream" analogue alongside curated memories.

## 2. LLM/SLM Abstraction Layer

SomaBrain emulates core LLM functions while remaining a lightweight orchestrator:

- **Representation Fusion** – `somabrain/context/state.py` maintains HRR-compressed embeddings,
  graph metadata, and governance scalars that together form an LLM-like latent state.
- **Multi-View Attention** – `somabrain/context/builder.py` computes retrieval weights across
  semantic similarity, graph centrality, and temporal decay, mirroring transformer heads.
- **Reasoning Loop** – `somabrain/planner.py` generates prompt hypotheses, evaluates utility, and
  returns the optimal plan for agent-side SLM execution.
- **Adaptive Parameters** – `somabrain/learning/adaptation.py` performs online convex optimisation on
  utility/retrieval weights and records updates in Postgres/Redis so the brain fine-tunes itself
  without touching model weights.
- **Evaluate/Feedback API** – `/context/evaluate` and `/context/feedback` expose the orchestrated
  bundle and collect agent outcomes. Feedback persists to Postgres (`feedback_events`,
  `token_usage`) and streams audit entries (`context.feedback`) for compliance.
- **Governance Coupling** – policy outputs from `somabrain/constitution` inject penalties and tags
  into every bundle, guaranteeing constitutional compliance at scale.

## 3. Request Lifecycle

1. **Ingress** – Agent sends request with signed headers. Envoy validates cert/JWT and sleeps the
   request only if thresholds are exceeded.
2. **Governance** – FastAPI handler loads constitution (cached in Redis) and verifies latest
   signature. OPA evaluated; decision and metadata captured.
3. **Audit** – `somabrain/audit.publish_event` produces a transactional record to Kafka with schema
   validation, capturing constitution hash, signature, request metadata, and trace ID. Redis Stream
   fallback buffers events if Kafka unreachable.
4. **Context Synthesis** – `somabrain/context/builder` fuses redis hot state, vector store results,
   and graph neighbours, producing weighted memories plus an HRR-compressed residual stream.
5. **Reasoning Loop** – `somabrain/planner` generates and scores prompt variants using the utility
   function; the best-ranked plan is attached to the response. No SLM inference happens inside the
   brain.
6. **Response** – Brain returns a `ContextBundle` (memories, residual vector, recommended prompt,
   governance directives) with trace/audit IDs for the agent to consume when calling its SLM.
7. **Feedback & Learning** – Agent invokes `/feedback` with results; SomaBrain records audit events,
   updates memory salience, and adjusts utility/retrieval weights via online optimisation.
8. **Observability** – Traces, metrics, and logs shipped to OTEL collector and stored in Prometheus/
   Loki/Tempo for dashboards and alerting.

## 4. Data Models & Storage

| Data Domain | Storage | Notes |
|-------------|---------|-------|
| Constitution documents | Redis JSON (active), Postgres (`constitution_versions`), S3 (`constitution/` bucket) | Stored with SHA3-512 hash, Ed25519 signatures, rotation metadata. |
| Audit events | Kafka topic `soma.audit` (immutable), S3 mirror | Enforced schema (`audit_event_v2.json`), includes trace ID, constitution hash, request metadata, decision. |
| Memories | Redis (`mem:<tenant>:<key>`), Qdrant vectors (`vector_id`), Postgres adjacency (`memory_edges`, `memory_payloads`) | All writes emit Kafka events with checksums; background worker reconciles discrepancies. |
| Token ledger | Postgres table (`token_usage`) | Aggregated per tenant, model, day. Snapshots to S3 daily. |
| Metrics & traces | Prometheus, Tempo, Loki via OTEL collector | Exported metrics include agent-side SLM latency (reported via feedback), audit fallback, constitution verification, cache hit rates. |

## 5. Scaling Strategies

- **API layer** – Horizontal Pod Autoscaler (CPU + queue length). Stateless pods capped by rate
  limiters in Redis to prevent noisy-neighbour tenants.
- **Kafka** – Partition topics to balance load; enable tiered storage if retention requirements grow.
- **Redis** – Use cluster mode with hash slots; for global deployments add geo-replicated read-only
  replicas.
- **Postgres** – Managed service with synchronous replicas for HA, read replicas for analytics,
  and Timescale compression for telemetry.
- **Vector store** – Partition by tenant/universe; replicate across AZs; incremental backups.

## 6. Security & Identity

- **Identity** – SPIFFE/SPIRE issues workload certificates; enforced by Envoy and services.
- **Secrets** – Vault or cloud secret manager rotates credentials; secrets injected via CSI driver.
- **API auth** – Bearer/JWT tokens validated with optional HS/RS keys; default tenant allowlist enforced on Evaluate/Feedback routes.
- **Network Policies** – Kubernetes policies restrict pod-to-pod traffic; service meshes (e.g., Istio
  or Linkerd) optional for additional policy enforcement.
- **Auditability** – Audit topic + object storage snapshots + Postgres indexes ensure every action is
  traceable. Alerts fire on audit fallback or schema violations.

## 7. Configuration Management

- All runtime configuration flows through environment variables documented in
  `docs/CONFIGURATION.md`. Sensitive overrides supplied by secret store.
- `scripts/dev_up.sh` inspects the host for occupied ports and writes `.env.local` and `ports.json`
  so developers and tests can target the correct addresses.
- Kubernetes deployments source config from ConfigMaps/Secrets generated by IaC.

## 8. Testing & Benchmarks

- **Unit tests** – run on every PR; focus on constitution, memory math, audit schema.
- **Integration tests** – executed against canonical compose stack in CI (`pytest -m integration`).
- **Load & benchmark tests** – `benchmarks/scale/` scripts produce RL throughput, latency, and
  resource usage metrics; results stored in object storage and compared against SLOs.
- **Chaos tests** – orchestrated via chaos tooling; must confirm auto-recovery and state
  correctness.

## 9. Deployment & Operations

- **CI/CD** – GitHub Actions pipelines lint, test, build Docker images, apply Terraform/Helm (via
  Argo CD or Flux). Releases require manual approval once health checks pass.
- **Release Strategy** – Blue/Green or canary depending on environment; automated rollback triggers
  when error rate > 1% or SLO breached for 5 minutes.
- **Runbooks** – Maintained alongside this file (see `docs/DEVELOPMENT_SETUP.md` and upcoming
  `ops/runbooks/`). Each critical component has a playbook.

## 10. Future Extensions

- Multi-region active/active deployments with global load balancing.
- Differential privacy and k-anonymity layers for sensitive memory payloads.
- Formal verification for end-to-end pipelines (beyond constitution & reward gate).

This document is living; update it whenever architecture decisions are made or components change.
