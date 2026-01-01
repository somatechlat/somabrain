# Technical Manual

**Purpose**: This manual explains how to deploy, operate, and manage SomaBrain in production environments.

**Audience**: System administrators, SREs, DevOps engineers, and platform teams.

**Prerequisites**: Experience with Docker, Kubernetes, monitoring systems, and production operations.

---

## Quick Navigation

- [Architecture](architecture.md) - System design and component interactions
- [Deployment](deployment.md) - Production deployment procedures
- [Configuration](configuration.md) - Environment variables and runtime settings
- [Monitoring](monitoring.md) - Dashboards, alerts, and observability
- Cognitive Threads
  - [Predictors](predictors.md) - Diffusion-backed predictors and configuration
  - [Diffusion Benchmarks](benchmarks_diffusion.md) - Accuracy & performance of Chebyshev/Lanczos
- [Runbooks](runbooks/) - Operational procedures
  - [Operations Overview](runbooks/operations-overview.md) - Day-two checklist
  - [SomaBrain API](runbooks/somabrain-api.md) - Main service operations
  - [Cognitive Threads](runbooks/cog-threads-operations.md) - Predictors & Integrator operations
  - [Redis Operations](runbooks/redis-operations.md) - Cache management
  - [Kafka Operations](runbooks/kafka-operations.md) - Message broker troubleshooting
  - [Postgres Operations](runbooks/postgres-operations.md) - Database operations
  - [Disaster Recovery](runbooks/disaster-recovery.md) - Backups and constitution restore
  - [Release & Health Gating](runbooks/release-health-gating.md) - Controlled rollouts
  - [Incident Response](runbooks/incident-response.md) - General incident procedures
- [Backup & Recovery](backup-and-recovery.md) - Disaster recovery procedures
- [Security](security/) - Security policies and controls
  - [Secrets Policy](security/secrets-policy.md) - Secrets management
  - [RBAC Matrix](security/rbac-matrix.md) - Access control

---

## System Overview

SomaBrain is a containerized cognitive memory platform with these core components:

- **SomaBrain API**: FastAPI service exposing memory and reasoning endpoints
- **Redis**: High-performance cache for working memory and session state
- **Postgres**: Persistent storage for configuration and audit logs
- **Kafka**: Message broker for audit trails and event streaming
- **OPA**: Policy engine for authorization and governance
- **Prometheus**: Metrics collection and alerting

## Retrieval API (Unified)

- Primary endpoint: POST `/recall`
  - Backed by the unified retrieval pipeline (vector + WM + graph + lexical + fusion + rerank).
  - Accepts either a JSON string (e.g., "find my favorite poem") or an object body (adds fields like retrievers, rerank, id/key/coord, mode, universe, top_k).
  - Response remains compatible with the MemoryRecallResponse shape for existing clients.


## Production Readiness

For production deployment:
1. Review [Architecture](architecture.md) to understand system design
2. Follow [Deployment](deployment.md) for installation procedures
3. Configure [Monitoring](monitoring.md) dashboards and alerts
4. Implement [Security](security/) policies
5. Train team on [Runbooks](runbooks/) procedures

---

**Verification**: Each procedure includes verification steps with expected output.

**Common Errors**: See individual runbooks for service-specific troubleshooting.

**References**:
- [User Manual](../user/index.md) for feature usage
- [Development Manual](../development/index.md) for code contributions
- [Runtime Configuration](configuration.md) for environment variables
