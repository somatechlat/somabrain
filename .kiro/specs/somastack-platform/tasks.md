# Implementation Plan: SomaStack Platform

## Overview

**SomaStack** is a unified, open-source platform for deploying the Soma AI Agent Ecosystem. This implementation plan covers **ALL 32 requirements** across **11 phases**, including both **infrastructure** AND **agentic cognitive implementation**.

**Document ID:** SOMASTACK-TASKS-2025-12  
**Version:** 5.0  
**Date:** 2025-12-21  
**Status:** CANONICAL — Single Source of Truth

## Key Principles

- **Language**: Python 3.11+ | **Testing**: pytest + hypothesis (property-based)
- **Infra**: Docker Compose (15GB RAM), Helm, Terraform
- **NO MOCKS**: Real infrastructure, real implementations, real data
- **VIBE Coding Rules**: Enforced throughout

## Requirements Coverage Matrix

| Req # | Requirement | Phase | Status |
|-------|-------------|-------|--------|
| 1 | Standalone Mode | 2-5 | Planned |
| 2 | SomaStack Mode | 1-5 | Planned |
| 3 | Kubernetes Mode | 10 | Planned |
| 4 | Progressive Deployment Pipeline | 10 | Planned |
| 5 | Apache Kafka Event Backbone | 1 | Planned |
| 6 | Apache Flink Stream Processing | 1 | Planned |
| 7 | Temporal Workflow Orchestration | 1 | Planned |
| 8 | Kong API Gateway | 1 | Planned |
| 9 | Linkerd Service Mesh | 7, 10 | Planned |
| 10 | PostgreSQL Database Cluster | 1 | Planned |
| 11 | Redis Cache Cluster | 1 | Planned |
| 12 | Milvus Vector Store | 1 | Planned |
| 13 | MinIO Object Storage | 1 | Planned |
| 14 | Apicurio Schema Registry | 1 | Planned |
| 15 | Debezium CDC | 1 | Planned |
| 16 | Distributed Tracing | 6 | Planned |
| 17 | Metrics (Prometheus + Grafana) | 6 | Planned |
| 18 | Log Aggregation | 6 | Planned |
| 19 | HashiCorp Vault Secrets | 7 | Planned |
| 20 | OPA Policy Enforcement | 7 | Planned |
| 21 | cert-manager Certificates | 7, 10 | Planned |
| 22 | Event Store | 8 | Planned |
| 23 | Saga Orchestration | 8 | Planned |
| 24 | Event Replay | 8 | Planned |
| 25 | Dead Letter Queue | 8 | Planned |
| 26 | Shared Python Library | 8 | Planned |
| 27 | CLI Tools | 9 | Planned |
| 28 | Beautiful Logging | 8 | Planned |
| 29 | Integration Testing | 12 | Planned |
| 30 | Chaos Engineering | 12 | Planned |
| 31 | AWS Production Deployment | 11 | Planned |
| 32 | Multi-Region / Disaster Recovery | 11 | Planned |

## Phase Dependency Graph

```
PHASE 1: INFRA ──► PHASE 2: SFM ──► PHASE 3: SB ──► PHASE 4: AGENT ──► PHASE 5: VOICE
                         │                │               │
                         └────────────────┴───────────────┴──► PHASE 6: OBSERVABILITY
                                                              PHASE 7: SECURITY
                                                              PHASE 8: SOMA-COMMON LIB
                                                              PHASE 9: CLI
                                                              PHASE 10: HELM
                                                              PHASE 11: TERRAFORM
                                                              PHASE 12: INTEGRATION TESTS
```

## Port Allocation (Conflict-Free)

| Component | Port Range | Primary Port |
|-----------|------------|--------------|
| SomaBrain | 30100-30199 | 9696 (API) |
| SomaAgent01 | 20000-20099, 21000-21099 | 21016 (Gateway) |
| SomaFractalMemory | 9500-9599 | 9595 (API) |
| AgentVoiceBox | 25000-25099 | 25000 (Voice) |
| Kafka | 9092-9094 | 9094 (External) |
| PostgreSQL | 5432-5433 | 5432 |
| Redis | 6379-6381 | 6379 |
| Milvus | 19530 | 19530 |
| Temporal | 7233, 8080 | 7233 (gRPC) |
| Flink | 8081 | 8081 (UI) |
| Kong | 8000-8001 | 8000 (Proxy) |
| Prometheus | 9090 | 9090 |
| Grafana | 3000 | 3000 |
| Jaeger | 16686 | 16686 |
| OPA | 8181 | 8181 |
| Vault | 8200 | 8200 |

---

## PHASE 1: INFRASTRUCTURE FOUNDATION

**Goal**: Establish shared infrastructure for all Soma components.  
**Requirements Covered**: 2, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15

---

### Task 1.1: Create SomaStack Directory Structure
- [ ] 1.1.1 Create `somastack/` root directory
- [ ] 1.1.2 Create subdirectories: `config/`, `helm/`, `terraform/`, `src/`, `cli/`, `tests/`, `docs/`
- [ ] 1.1.3 Create `somastack/Makefile` with targets:
  - `somastack-up`: Start full stack
  - `somastack-down`: Stop all services
  - `somastack-status`: Health check all components
  - `somastack-logs`: Tail logs
- [ ] 1.1.4 Create `somastack/README.md` with architecture overview
- **Requirements**: 2.5, 27.1

### Task 1.2: Create Kafka Configuration (KRaft Mode)
- [ ] 1.2.1 Create `config/kafka/server.properties`
  - KRaft mode (no ZooKeeper dependency)
  - 6 partitions default, snappy compression
  - 7-day retention, exactly-once semantics
  - JVM tuning for 1.5GB heap
- [ ] 1.2.2 Create `config/kafka/topics.yaml`
  - Namespaces: `soma.brain.*`, `soma.agent.*`, `soma.memory.*`, `soma.voice.*`, `soma.stack.*`
  - Topic configurations per namespace
- **Requirements**: 5.1, 5.2, 5.4, 5.5, 5.6

### Task 1.3: Create Flink Configuration
- [ ] 1.3.1 Create `config/flink/flink-conf.yaml`
  - RocksDB state backend
  - 30s checkpoints to MinIO
  - Prometheus metrics exporter
- [ ] 1.3.2 Create `config/flink/log4j-console.properties`
  - JSON structured logging format
- **Requirements**: 6.2, 6.3, 6.5, 6.8

### Task 1.4: Create Temporal Configuration
- [ ] 1.4.1 Create `config/temporal/dynamicconfig.yaml`
  - PostgreSQL backend configuration
  - Namespace isolation settings
- [ ] 1.4.2 Create `config/temporal/development.yaml`
  - Local development overrides
- **Requirements**: 7.2, 7.3, 7.5

### Task 1.5: Create Kong API Gateway Configuration
- [ ] 1.5.1 Create `config/kong/kong.yaml`
  - Service routes for all Soma components
  - Rate limiting configuration
  - Correlation ID injection
- [ ] 1.5.2 Create `config/kong/ssl/` directory with self-signed certs
- **Requirements**: 8.1, 8.2, 8.4, 8.5, 8.6

### Task 1.6: Create PostgreSQL Configuration
- [ ] 1.6.1 Create `config/postgres/postgresql.conf`
  - WAL configuration for CDC (Debezium)
  - Connection pooling settings
  - Autovacuum tuning
- [ ] 1.6.2 Create `config/postgres/pg_hba.conf` - Authentication rules
- [ ] 1.6.3 Create `config/postgres/init/01-databases.sql`
  - Create databases: somabrain, somaagent, somamemory, temporal
- [ ] 1.6.4 Create `config/postgres/init/02-extensions.sql`
  - Extensions: uuid-ossp, pgcrypto, pg_trgm
- [ ] 1.6.5 Create `config/postgres/init/03-events.sql`
  - Event store table with partitioning
  - Indexes for trace_id, correlation_id, tenant_id
- [ ] 1.6.6 Create `config/postgres/init/04-sagas.sql`
  - Saga state table
  - Idempotency keys table
  - Outbox table for transactional messaging
- [ ] 1.6.7 Create `config/postgres/init/05-users.sql`
  - Service users with least-privilege grants
- **Requirements**: 10.3, 10.4, 10.7, 22.1, 22.2, 23.3, 24.4

### Task 1.7: Create Redis Configuration
- [ ] 1.7.1 Create `config/redis/redis.conf`
  - AOF persistence enabled
  - LRU eviction policy
  - 512MB maxmemory limit
- **Requirements**: 11.6, 11.7

### Task 1.8: Create Milvus Configuration
- [ ] 1.8.1 Create `config/milvus/milvus.yaml`
  - etcd metadata storage
  - MinIO object storage
  - Query node tuning for 2GB RAM
- **Requirements**: 12.2, 12.4

### Task 1.9: Create MinIO Configuration
- [ ] 1.9.1 Create `config/minio/init-buckets.sh`
  - Buckets: flink-checkpoints, postgres-backups, event-archive, model-artifacts
- **Requirements**: 13.3, 13.4, 13.5

### Task 1.10: Create Apicurio Schema Registry Configuration
- [ ] 1.10.1 Create `config/apicurio/application.properties`
  - PostgreSQL storage backend
  - Compatibility rules (BACKWARD default)
- [ ] 1.10.2 Create `config/apicurio/schemas/` directory
  - Initial Avro schemas for SomaEvent
- **Requirements**: 14.1, 14.2, 14.3, 14.4, 14.8

### Task 1.11: Create Debezium CDC Configuration
- [ ] 1.11.1 Create `config/debezium/postgres-connector.json`
  - PostgreSQL logical replication
  - Table filtering configuration
  - Kafka topic routing
- **Requirements**: 15.1, 15.2, 15.3, 15.4, 15.5

### Task 1.12: Create Docker Compose Infrastructure
- [ ] 1.12.1 Create `somastack/docker-compose.yaml`
  - All infrastructure services with production-like settings
  - Resource limits (15GB total budget)
  - Health checks for all services
  - Named volumes for persistence
  - `somastack_net` shared network
  - Profiles: `infra`, `soma`, `observability`, `security`, `full`
- **Requirements**: 2.2, 2.3, 2.6

### Task 1.13: CHECKPOINT - Verify Infrastructure
- [ ] 1.13.1 Run `docker compose config` to validate syntax
- [ ] 1.13.2 Run `docker compose --profile infra up -d`
- [ ] 1.13.3 Verify health: Kafka, PostgreSQL, Redis, Milvus, MinIO, Temporal, Flink
- [ ] 1.13.4 Verify Apicurio Schema Registry accessible
- [ ] 1.13.5 Verify Debezium connector registered
- [ ] 1.13.6 Document any issues and resolutions

---

## PHASE 2: SOMAFRACTALMEMORY (SFM) INTEGRATION

**Goal**: Integrate memory service as foundation for all Soma services.  
**Requirements Covered**: 1, 2

---

### Task 2.1: Add SFM Deployment Mode Detection
- [ ] 2.1.1 Create `somafractalmemory/common/deployment.py`
  - `DeploymentMode` enum: STANDALONE, SOMASTACK, K8S
  - Auto-detect from `SOMA_DEPLOY_MODE` env var
  - Configuration loader per mode
- [ ] 2.1.2 Update `somafractalmemory/docker-compose.yml`
  - Add `somastack` profile
  - External network `somastack_net` when in somastack mode
  - Configure env vars for shared infrastructure
- [ ] 2.1.3 Create `somafractalmemory/SOMASTACK.md`
  - Document deployment modes
  - Port range 9500-9599
  - Environment variables reference
- **Requirements**: 1.1, 1.3, 2.1, 2.3, 2.4

### Task 2.2: Update SFM Documentation
- [ ] 2.2.1 Update `somafractalmemory/README.md`
  - Add SomaStack integration section
  - Update architecture diagram
- [ ] 2.2.2 Update `somafractalmemory/docs/technical-manual/deployment-docker.md`
  - Add somastack mode instructions
- **Requirements**: 26.4

### Task 2.3: CHECKPOINT - Verify SFM Integration
- [ ] 2.3.1 Start infra: `docker compose --profile infra up -d`
- [ ] 2.3.2 Start SFM: `SOMA_DEPLOY_MODE=somastack docker compose up -d`
- [ ] 2.3.3 Verify: `curl http://localhost:9595/healthz`
- [ ] 2.3.4 Verify Milvus, PostgreSQL, Redis connections
- [ ] 2.3.5 Run SFM test suite: `pytest somafractalmemory/tests/`

---

## PHASE 3: SOMABRAIN (SB) INTEGRATION

**Goal**: Integrate cognitive processing service with SomaFractalMemory.  
**Requirements Covered**: 1, 2

---

### Task 3.1: Add SB Deployment Mode Detection
- [ ] 3.1.1 Create `somabrain/common/deployment.py`
  - `DeploymentMode` enum: STANDALONE, SOMASTACK, K8S
  - Auto-detect from `SOMA_DEPLOY_MODE` env var
- [ ] 3.1.2 Update `somabrain/docker-compose.yml`
  - Add `somastack` profile
  - External network `somastack_net`
  - Point `SOMABRAIN_MEMORY_HTTP_ENDPOINT` to SFM
- [ ] 3.1.3 Create `somabrain/SOMASTACK.md`
  - Document deployment modes
  - Ports: 30100-30199 (standalone), 9696 (API)
  - Document dependency on SomaFractalMemory
- **Requirements**: 1.1, 1.3, 2.1, 2.3, 2.4

### Task 3.2: Update SB Documentation
- [ ] 3.2.1 Update `somabrain/README.md`
  - Add SomaStack integration section
  - Update topology diagram
- [ ] 3.2.2 Update `somabrain/docs/technical-manual/architecture.md`
  - Add SomaStack architecture diagram
- [ ] 3.2.3 Update `somabrain/docs/technical-manual/deployment.md`
  - Add somastack mode instructions
- **Requirements**: 26.4

### Task 3.3: CHECKPOINT - Verify SB Integration
- [ ] 3.3.1 Ensure infra + SFM running
- [ ] 3.3.2 Start SB: `SOMA_DEPLOY_MODE=somastack docker compose up -d`
- [ ] 3.3.3 Verify: `curl http://localhost:9696/health`
- [ ] 3.3.4 Verify SFM connection, Kafka connection
- [ ] 3.3.5 Run SB test suite: `pytest somabrain/tests/`

---

## PHASE 4: SOMAAGENT01 INTEGRATION

**Goal**: Integrate agent orchestration with cognitive services.  
**Requirements Covered**: 1, 2

---

### Task 4.1: Add Agent Deployment Mode Detection
- [ ] 4.1.1 Create `somaAgent01/src/core/config/deployment.py`
  - `DeploymentMode` enum: STANDALONE, SOMASTACK, K8S
  - Auto-detect from `SOMA_DEPLOY_MODE` env var
- [ ] 4.1.2 Update `somaAgent01/docker-compose.yaml`
  - Add `somastack` profile
  - External network `somastack_net`
  - Point to SomaBrain and SomaFractalMemory endpoints
- [ ] 4.1.3 Create `somaAgent01/SOMASTACK.md`
  - Document deployment modes
  - Ports: 20000-20099, 21000-21099
  - Document dependencies on SomaBrain and SomaFractalMemory
- **Requirements**: 1.1, 1.3, 2.1, 2.3, 2.4

### Task 4.2: Implement SomaBrain Cognitive Integration
**CRITICAL: This is the AGENTIC implementation - the core AI functionality**

#### Task 4.2.1: Core Cognitive Endpoints (soma_client.py)
- [ ] 4.2.1.1 Implement `adaptation_reset()` method
  - POST `/context/adaptation/reset`
  - Parameters: `tenant_id`, `base_lr`, `reset_history`
- [ ] 4.2.1.2 Implement `act()` method
  - POST `/act`
  - Parameters: `task`, `universe`, `session_id`
- [ ] 4.2.1.3 Implement `util_sleep()` method
  - POST `/api/util/sleep`
  - Parameters: `target_state`, `ttl_seconds`, `async_mode`, `trace_id`
- [ ] 4.2.1.4 Implement `brain_sleep_mode()` method
  - POST `/api/brain/sleep_mode`
  - Support states: active, light, deep, freeze
- **Requirements**: SomaBrain API integration

#### Task 4.2.2: Neuromodulation System Integration
- [ ] 4.2.2.1 Verify `get_neuromodulators()` works with SomaBrain
  - GET `/neuromodulators`
  - Returns: dopamine, serotonin, noradrenaline, acetylcholine
- [ ] 4.2.2.2 Verify `update_neuromodulators()` works with SomaBrain
  - POST `/neuromodulators`
  - Clamp values to physiological ranges
- [ ] 4.2.2.3 Implement neuromodulator decay in cognitive loop
  - Apply natural decay each iteration
  - Update agent behavior based on levels
- **Requirements**: Cognitive processing, neuromodulation

#### Task 4.2.3: Adaptation State Management
- [ ] 4.2.3.1 Implement `get_adaptation_state()` integration
  - GET `/context/adaptation/state`
  - Cache in `agent.data["adaptation_state"]`
- [ ] 4.2.3.2 Implement `reset_adaptation_state()` wrapper
  - Clear local cache on success
  - Support `base_lr` and `reset_history` parameters
- [ ] 4.2.3.3 Apply adaptation weights to agent behavior
  - Retrieval weights: alpha, beta, gamma, tau
  - Utility weights: lambda_, mu, nu
- **Requirements**: Cognitive adaptation

#### Task 4.2.4: Sleep Cycle / Memory Consolidation
- [ ] 4.2.4.1 Implement `transition_sleep_state()` wrapper
  - Support all states: active, light, deep, freeze
  - Optional TTL for auto-revert
- [ ] 4.2.4.2 Implement `get_sleep_status()` wrapper
  - GET `/sleep/status`
  - Track last NREM/REM timestamps
- [ ] 4.2.4.3 Update cognitive.py sleep logic
  - Trigger consolidation at high cognitive load (>0.8)
  - Use `brain_sleep_mode()` instead of `sleep_cycle()`
  - Reset cognitive load after sleep
- **Requirements**: Memory consolidation, sleep cycles

#### Task 4.2.5: Admin & Service Management (ADMIN MODE)
- [ ] 4.2.5.1 Implement `list_services()` - GET `/admin/services`
- [ ] 4.2.5.2 Implement `get_service_status(name)` - GET `/admin/services/{name}`
- [ ] 4.2.5.3 Implement `start_service(name)` - POST `/admin/services/{name}/start`
- [ ] 4.2.5.4 Implement `stop_service(name)` - POST `/admin/services/{name}/stop`
- [ ] 4.2.5.5 Implement `restart_service(name)` - POST `/admin/services/{name}/restart`
- **Requirements**: Admin service management

#### Task 4.2.6: Cognitive Thread Management
- [ ] 4.2.6.1 Implement `create_thread(tenant_id, options)` - POST `/cognitive/thread`
- [ ] 4.2.6.2 Implement `get_next_option(tenant_id)` - GET `/cognitive/thread/next`
- [ ] 4.2.6.3 Implement `reset_thread(tenant_id)` - PUT `/cognitive/thread/reset`
- **Requirements**: Cognitive thread lifecycle

#### Task 4.2.7: Diagnostics & Feature Flags (ADMIN MODE)
- [ ] 4.2.7.1 Implement `micro_diag()` - GET `/micro/diag`
- [ ] 4.2.7.2 Implement `get_features()` - GET `/admin/features`
- [ ] 4.2.7.3 Implement `update_features(overrides)` - POST `/admin/features`
- **Requirements**: Diagnostics, feature management

### Task 4.3: Update Agent Documentation
- [ ] 4.3.1 Update `somaAgent01/README.md`
  - Add SomaStack integration section
  - Document cognitive integration
- [ ] 4.3.2 Update `somaAgent01/docs/technical-manual/architecture.md`
  - Add SomaStack diagram
  - Document SomaBrain integration flow
- [ ] 4.3.3 Update `somaAgent01/docs/technical-manual/deployment.md`
  - Add somastack mode instructions
- **Requirements**: 26.4

### Task 4.4: Create SomaBrain Integration Tests
- [ ] 4.4.1 Create `somaAgent01/tests/test_somabrain_integration.py`
  - `test_adaptation_reset` - Verify reset clears state
  - `test_act_execution` - Verify action execution with salience
  - `test_sleep_state_transitions` - Verify all state transitions
  - `test_neuromodulator_update` - Verify clamping and persistence
  - `test_cognitive_threads` - Verify thread lifecycle
- **Requirements**: Integration testing

### Task 4.5: CHECKPOINT - Verify Agent Integration
- [ ] 4.5.1 Ensure infra + SFM + SB running
- [ ] 4.5.2 Start Agent: `SOMA_DEPLOY_MODE=somastack docker compose up -d`
- [ ] 4.5.3 Verify: `curl http://localhost:21016/v1/health`
- [ ] 4.5.4 Verify SomaBrain, Kafka, Temporal connections
- [ ] 4.5.5 Run Agent test suite: `pytest somaAgent01/tests/`
- [ ] 4.5.6 Verify cognitive integration: neuromodulators, adaptation, sleep

---

## PHASE 5: AGENTVOICEBOX INTEGRATION

**Goal**: Integrate voice interface with agent orchestration.  
**Requirements Covered**: 1, 2

---

### Task 5.1: Add VoiceBox Deployment Mode Detection
- [ ] 5.1.1 Create `agentVoiceBox/ovos_voice_agent/deployment.py`
  - `DeploymentMode` enum: STANDALONE, SOMASTACK, K8S
  - Auto-detect from `SOMA_DEPLOY_MODE` env var
- [ ] 5.1.2 Create `agentVoiceBox/docker-compose.yml`
  - Voice agent service
  - STT/TTS workers
  - Add `somastack` profile
  - External network `somastack_net`
- [ ] 5.1.3 Create `agentVoiceBox/SOMASTACK.md`
  - Document deployment modes
  - Ports: 25000-25099
  - Document dependency on SomaAgent01
- **Requirements**: 1.1, 1.3, 2.1, 2.3, 2.4

### Task 5.2: Update VoiceBox Documentation
- [ ] 5.2.1 Rewrite `agentVoiceBox/README.md`
  - Complete rewrite for voice agent functionality
  - Add SomaStack integration section
- [ ] 5.2.2 Create `agentVoiceBox/docs/technical-manual/architecture.md`
  - Voice pipeline architecture
  - STT/TTS provider abstraction
- **Requirements**: 26.4

### Task 5.3: CHECKPOINT - Verify VoiceBox Integration
- [ ] 5.3.1 Ensure full stack running (infra + SFM + SB + Agent)
- [ ] 5.3.2 Start VoiceBox: `SOMA_DEPLOY_MODE=somastack docker compose up -d`
- [ ] 5.3.3 Verify health endpoint
- [ ] 5.3.4 Verify SomaAgent01 connection

---

## PHASE 6: OBSERVABILITY

**Goal**: Implement distributed tracing, metrics, and logging.  
**Requirements Covered**: 16, 17, 18

---

### Task 6.1: Create Tracing Configuration (Jaeger + OpenTelemetry)
- [ ] 6.1.1 Create `config/jaeger/sampling.json`
  - 100% sampling for errors
  - 10% sampling for success
- [ ] 6.1.2 Create `config/otel/otel-collector-config.yaml`
  - W3C Trace Context propagation
  - Export to Jaeger
- **Requirements**: 16.1, 16.2, 16.4, 16.7

### Task 6.2: Create Metrics Configuration (Prometheus + Grafana)
- [ ] 6.2.1 Create `config/prometheus/prometheus.yml`
  - Scrape configs for all Soma services
  - 15-day retention
- [ ] 6.2.2 Create `config/prometheus/recording_rules.yml`
  - Aggregation rules for common queries
- [ ] 6.2.3 Create `config/prometheus/alerts/somastack.yml`
  - Alert rules for health and resources
- [ ] 6.2.4 Create `config/grafana/provisioning/datasources/datasources.yaml`
  - Prometheus, Loki, Jaeger datasources
- [ ] 6.2.5 Create `config/grafana/provisioning/dashboards/somastack-overview.json`
  - All services health dashboard
- [ ] 6.2.6 Create `config/grafana/provisioning/dashboards/kafka.json`
  - Kafka throughput, lag, partitions
- [ ] 6.2.7 Create `config/grafana/provisioning/dashboards/flink.json`
  - Checkpoints, backpressure, throughput
- [ ] 6.2.8 Create `config/grafana/provisioning/dashboards/postgres.json`
  - Connections, queries, replication
- **Requirements**: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6

### Task 6.3: Create Logging Configuration (Loki + Promtail)
- [ ] 6.3.1 Create `config/loki/loki-config.yaml`
  - 30-day retention
  - Label-based indexing
- [ ] 6.3.2 Create `config/promtail/promtail-config.yaml`
  - Docker log collection
  - Kubernetes metadata enrichment
- **Requirements**: 18.1, 18.2, 18.3, 18.4, 18.5

### Task 6.4: Add Observability to Docker Compose
- [ ] 6.4.1 Update `somastack/docker-compose.yaml`
  - Add `observability` profile
  - Add Jaeger, Prometheus, Grafana, Loki, Promtail services
- **Requirements**: 16.4, 17.1, 18.1

### Task 6.5: CHECKPOINT - Verify Observability
- [ ] 6.5.1 Start: `docker compose --profile observability up -d`
- [ ] 6.5.2 Verify Jaeger: `http://localhost:16686`
- [ ] 6.5.3 Verify Prometheus: `http://localhost:9090`
- [ ] 6.5.4 Verify Grafana: `http://localhost:3000`
- [ ] 6.5.5 Verify traces flow from Soma services
- [ ] 6.5.6 Verify logs aggregated in Loki

---

## PHASE 7: SECURITY

**Goal**: Implement secrets management, policy enforcement, and certificates.  
**Requirements Covered**: 9, 19, 20, 21

---

### Task 7.1: Create HashiCorp Vault Configuration
- [ ] 7.1.1 Create `config/vault/vault-config.hcl`
  - Storage backend configuration
  - Listener configuration
- [ ] 7.1.2 Create `config/vault/policies/soma-services.hcl`
  - Service-specific secret access policies
- [ ] 7.1.3 Create `config/vault/init-secrets.sh`
  - Initialize secrets for all services
  - Database credentials
  - API keys
- **Requirements**: 19.1, 19.2, 19.3, 19.4, 19.5

### Task 7.2: Create OPA Policy Configuration
- [ ] 7.2.1 Create `config/opa/policies/authz.rego`
  - Base authorization rules
  - Tenant isolation
- [ ] 7.2.2 Create `config/opa/policies/rbac.rego`
  - Role-based access control
  - Service-to-service permissions
- [ ] 7.2.3 Create `config/opa/data.json`
  - Policy data (roles, permissions)
- **Requirements**: 20.1, 20.2, 20.3, 20.4, 20.5

### Task 7.3: Create Linkerd Service Mesh Configuration
- [ ] 7.3.1 Create `config/linkerd/linkerd-config.yaml`
  - mTLS configuration
  - Sidecar injection settings
- [ ] 7.3.2 Create `config/linkerd/service-profiles/`
  - Service profiles for each Soma component
  - Retry and timeout policies
- **Requirements**: 9.1, 9.2, 9.3, 9.4, 9.5

### Task 7.4: Create cert-manager Configuration
- [ ] 7.4.1 Create `config/cert-manager/cluster-issuer.yaml`
  - Let's Encrypt issuer for public endpoints
  - Internal CA for service mesh
- [ ] 7.4.2 Create `config/cert-manager/certificates/`
  - Certificate definitions for each service
- **Requirements**: 21.1, 21.2, 21.3, 21.4, 21.5

### Task 7.5: Add Security to Docker Compose
- [ ] 7.5.1 Update `somastack/docker-compose.yaml`
  - Add `security` profile
  - Add Vault, OPA services
- **Requirements**: 19.1, 20.1

### Task 7.6: CHECKPOINT - Verify Security
- [ ] 7.6.1 Start: `docker compose --profile security up -d`
- [ ] 7.6.2 Verify Vault: `curl http://localhost:8200/v1/sys/health`
- [ ] 7.6.3 Verify OPA: `curl http://localhost:8181/health`
- [ ] 7.6.4 Test authorization policy decisions
- [ ] 7.6.5 Verify secret injection works

---

## PHASE 8: SOMA-COMMON LIBRARY

**Goal**: Create shared Python library for event sourcing, tracing, and sagas.  
**Requirements Covered**: 22, 23, 24, 25, 26, 28

---

### Task 8.1: Create Library Structure
- [ ] 8.1.1 Create `somastack/src/soma_common/__init__.py`
  - Package init with version
- [ ] 8.1.2 Create `somastack/src/soma_common/py.typed`
  - PEP 561 type hints marker
- [ ] 8.1.3 Create `somastack/pyproject.toml`
  - Dependencies: aiokafka, asyncpg, opentelemetry-sdk, pydantic
- **Requirements**: 26.3, 26.4

### Task 8.2: Implement Event Models
- [ ] 8.2.1 Create `src/soma_common/events/types.py`
  - `EventType` enum with all standard types
- [ ] 8.2.2 Create `src/soma_common/events/models.py`
  - `Event` dataclass with all required fields
  - Avro schema generation
- [ ] 8.2.3* **Property Test: Event Field Completeness**
  - *For any* Event, all required fields (event_id, trace_id, correlation_id, service_id, tenant_id, timestamp, event_type, payload) must be present and non-null
  - **Validates: Requirement 22.1**
- **Requirements**: 22.1, 22.3, 22.4

### Task 8.3: Implement EventStore
- [ ] 8.3.1 Create `src/soma_common/events/store.py`
  - `EventStore` class with `publish()`, `query()`, `replay()`
  - Kafka + PostgreSQL atomic write
- [ ] 8.3.2* **Property Test: Atomic Persistence**
  - *For any* event published, it appears in both Kafka and PostgreSQL, or neither
  - **Validates: Requirement 22.2**
- [ ] 8.3.3* **Property Test: Event Ordering Guarantee**
  - *For any* two events with same partition key, if E1.timestamp < E2.timestamp, E1 processed before E2
  - **Validates: Requirement 22.5**
- **Requirements**: 22.2, 22.5, 24.1

### Task 8.4: Implement Saga Orchestrator
- [ ] 8.4.1 Create `src/soma_common/sagas/models.py`
  - `SagaStatus` enum
  - `SagaStep` dataclass
  - `Saga` dataclass
- [ ] 8.4.2 Create `src/soma_common/sagas/orchestrator.py`
  - `SagaOrchestrator` with `start_saga()`, `get_saga()`, `compensate()`
- [ ] 8.4.3* **Property Test: Saga Compensation Order**
  - *For any* saga failing at step N, compensations execute in order N-1, N-2, ..., 1
  - **Validates: Requirement 23.2**
- [ ] 8.4.4* **Property Test: Saga State Recovery**
  - *For any* saga, after restart, state recoverable from PostgreSQL
  - **Validates: Requirement 23.3**
- **Requirements**: 23.1, 23.2, 23.3

### Task 8.5: Implement Transaction Tracer
- [ ] 8.5.1 Create `src/soma_common/tracing/tracer.py`
  - `TransactionTracer` class
  - OpenTelemetry integration
- [ ] 8.5.2 Create `src/soma_common/tracing/context.py`
  - `TraceContext` dataclass
  - Header injection/extraction
- **Requirements**: 16.1, 16.2, 16.3

### Task 8.6: Implement Decorators
- [ ] 8.6.1 Create `src/soma_common/decorators.py`
  - `@trace_transaction` decorator
  - `@with_compensation(action)` decorator
  - `TransactionScope` context manager
- **Requirements**: 26.1

### Task 8.7: Implement Beautiful Logging
- [ ] 8.7.1 Create `src/soma_common/logging/formatters.py`
  - `SomaStackFormatter` with emoji indicators
  - `SomaStackJSONFormatter` for structured output
  - Emoji mapping: ✅ SUCCESS, ❌ ERROR, ⚠️ WARNING, ℹ️ INFO, 🔍 DEBUG
  - Service emojis: 🧠 COGNITIVE, 🤖 AGENT, 💾 MEMORY, 🎤 VOICE
- [ ] 8.7.2 Create `src/soma_common/logging/config.py`
  - `configure_logging()` function
  - Console/JSON mode switching
- [ ] 8.7.3* **Property Test: Structured Logging Format**
  - *For any* log entry, contains required fields (timestamp, level, service, trace_id, message) and correct emoji for level
  - **Validates: Requirements 28.1, 28.2**
- **Requirements**: 28.1, 28.2, 28.3, 28.4, 28.5, 28.6

### Task 8.8: Implement Replay Engine
- [ ] 8.8.1 Create `src/soma_common/replay/engine.py`
  - `ReplayEngine` class
  - Filtering by trace_id, time range, service, event type
  - Idempotency checking
- [ ] 8.8.2* **Property Test: Replay Idempotency**
  - *For any* event replayed multiple times with same idempotency_key, side effects occur exactly once
  - **Validates: Requirement 24.4**
- **Requirements**: 24.1, 24.2, 24.4

### Task 8.9: Implement DLQ Handler
- [ ] 8.9.1 Create `src/soma_common/dlq/handler.py`
  - `DLQHandler` class
  - `capture_failed_event()`, `list_dlq_events()`, `retry_event()`
- [ ] 8.9.2* **Property Test: DLQ Capture and Preservation**
  - *For any* event failing max_retries times, appears in DLQ with original payload and error details
  - **Validates: Requirements 25.1, 25.2**
- **Requirements**: 25.1, 25.2, 25.3, 25.4

### Task 8.10: CHECKPOINT - Verify soma-common Library
- [ ] 8.10.1 Run `pytest somastack/tests/`
- [ ] 8.10.2 Verify all property tests pass
- [ ] 8.10.3 Verify type hints with mypy
- **Requirements**: 26.5

---

## PHASE 9: CLI TOOLS

**Goal**: Create SomaStack CLI for platform management.  
**Requirements Covered**: 27

---

### Task 9.1: Create CLI Structure
- [ ] 9.1.1 Create `somastack/cli/somastack/__init__.py`
- [ ] 9.1.2 Create `somastack/cli/somastack/main.py`
  - Click app entry point
- [ ] 9.1.3 Create `somastack/cli/pyproject.toml`
  - CLI package configuration
- **Requirements**: 27.2

### Task 9.2: Implement CLI Commands
- [ ] 9.2.1 Create `cli/somastack/commands/up.py`
  - `somastack up [--mode standalone|somastack|k8s]`
- [ ] 9.2.2 Create `cli/somastack/commands/down.py`
  - `somastack down`
- [ ] 9.2.3 Create `cli/somastack/commands/status.py`
  - `somastack status` with health table
- [ ] 9.2.4 Create `cli/somastack/commands/logs.py`
  - `somastack logs [service]`
- [ ] 9.2.5 Create `cli/somastack/commands/events.py`
  - `somastack events list [--trace-id X]`
  - `somastack events replay [--from TIME]`
- [ ] 9.2.6 Create `cli/somastack/commands/saga.py`
  - `somastack saga list`
  - `somastack saga inspect [saga-id]`
- [ ] 9.2.7 Create `cli/somastack/commands/dlq.py`
  - `somastack dlq list`
  - `somastack dlq retry [event-id]`
- [ ] 9.2.8 Add shell completion support
- **Requirements**: 27.1, 27.3

### Task 9.3: Property Tests for CLI
- [ ] 9.3.1* **Property Test: Port Range Isolation**
  - *For any* two components, their port ranges must not overlap
  - **Validates: Requirement 1.3**
- [ ] 9.3.2* **Property Test: Environment Variable Discovery**
  - *For any* component in somastack mode, correct infrastructure endpoints discovered via env vars
  - **Validates: Requirement 2.4**

### Task 9.4: CHECKPOINT - Verify CLI
- [ ] 9.4.1 Install CLI: `pip install -e somastack/cli/`
- [ ] 9.4.2 Test all commands
- [ ] 9.4.3 Verify shell completion

---

## PHASE 10: HELM CHARTS

**Goal**: Create Kubernetes deployment via Helm umbrella chart.  
**Requirements Covered**: 3, 4, 9, 21

---

### Task 10.1: Create Umbrella Chart Structure
- [ ] 10.1.1 Create `helm/somastack/Chart.yaml`
  - Umbrella chart definition
- [ ] 10.1.2 Create `helm/somastack/values.yaml`
  - Default values
- [ ] 10.1.3 Create `helm/somastack/values-dev.yaml`
  - Development overrides
- [ ] 10.1.4 Create `helm/somastack/values-staging.yaml`
  - Staging overrides
- [ ] 10.1.5 Create `helm/somastack/values-prod.yaml`
  - Production overrides with HA
- **Requirements**: 3.1, 3.2

### Task 10.2: Create Infrastructure Sub-Charts
- [ ] 10.2.1 Create `helm/somastack/charts/kafka/`
  - Strimzi operator templates
- [ ] 10.2.2 Create `helm/somastack/charts/postgresql/`
  - CloudNativePG templates
- [ ] 10.2.3 Create `helm/somastack/charts/redis/`
  - Redis templates
- [ ] 10.2.4 Create `helm/somastack/charts/milvus/`
  - Milvus templates
- [ ] 10.2.5 Create `helm/somastack/charts/temporal/`
  - Temporal templates
- [ ] 10.2.6 Create `helm/somastack/charts/flink/`
  - Flink operator templates
- **Requirements**: 3.3, 5.7, 6.7, 7.7, 10.1, 12.8

### Task 10.3: Create Observability Sub-Chart
- [ ] 10.3.1 Create `helm/somastack/charts/observability/`
  - Prometheus, Grafana, Jaeger, Loki
- **Requirements**: 3.3, 16.5, 17.5

### Task 10.4: Create Security Sub-Chart
- [ ] 10.4.1 Create `helm/somastack/charts/security/`
  - OPA, Vault, cert-manager, Linkerd
- **Requirements**: 3.3, 9.1, 19.1, 20.7, 21.1

### Task 10.5: Create Soma Service Charts
- [ ] 10.5.1 Create `helm/somastack/charts/somabrain/`
  - SomaBrain deployment with HPA, PDB
- [ ] 10.5.2 Create `helm/somastack/charts/somaagent/`
  - SomaAgent01 deployment with HPA, PDB
- [ ] 10.5.3 Create `helm/somastack/charts/somamemory/`
  - SomaFractalMemory deployment with HPA, PDB
- [ ] 10.5.4 Create `helm/somastack/charts/somavoice/`
  - AgentVoiceBox deployment with HPA, PDB
- **Requirements**: 3.6, 3.7

### Task 10.6: Create ArgoCD Configuration
- [ ] 10.6.1 Create `helm/somastack/argocd/application.yaml`
  - ArgoCD Application definition
- [ ] 10.6.2 Create `helm/somastack/argocd/project.yaml`
  - ArgoCD Project definition
- [ ] 10.6.3 Configure canary deployment support
- [ ] 10.6.4 Configure blue-green deployment support
- **Requirements**: 4.4, 4.5, 4.6

### Task 10.7: CHECKPOINT - Verify Helm Charts
- [ ] 10.7.1 Run `helm lint helm/somastack/`
- [ ] 10.7.2 Run `helm template somastack helm/somastack/`
- [ ] 10.7.3 Test deployment to minikube/kind

---

## PHASE 11: TERRAFORM (AWS)

**Goal**: Create AWS production deployment via Terraform.  
**Requirements Covered**: 31, 32

---

### Task 11.1: Create Terraform Module Structure
- [ ] 11.1.1 Create `terraform/modules/eks/`
  - EKS cluster with managed node groups
  - IRSA (IAM Roles for Service Accounts)
- [ ] 11.1.2 Create `terraform/modules/msk/`
  - Managed Kafka (MSK) cluster
- [ ] 11.1.3 Create `terraform/modules/rds/`
  - PostgreSQL with Multi-AZ
- [ ] 11.1.4 Create `terraform/modules/elasticache/`
  - Redis cluster
- [ ] 11.1.5 Create `terraform/modules/s3/`
  - S3 buckets for storage
- [ ] 11.1.6 Create `terraform/modules/networking/`
  - VPC with private subnets
  - VPC endpoints for AWS services
- **Requirements**: 31.1, 31.4, 31.5

### Task 11.2: Create Environment Configurations
- [ ] 11.2.1 Create `terraform/environments/dev/`
  - Development environment
- [ ] 11.2.2 Create `terraform/environments/staging/`
  - Staging environment
- [ ] 11.2.3 Create `terraform/environments/prod/`
  - Production environment with HA
- **Requirements**: 31.3

### Task 11.3: Create Multi-Region Support
- [ ] 11.3.1 Create `terraform/modules/multi-region/`
  - Active-passive deployment
- [ ] 11.3.2 Configure MirrorMaker 2 for Kafka replication
- [ ] 11.3.3 Configure cross-region PostgreSQL read replicas
- [ ] 11.3.4 Create failover runbooks
- **Requirements**: 32.1, 32.2, 32.3, 32.4, 32.5, 32.6

### Task 11.4: CHECKPOINT - Verify Terraform
- [ ] 11.4.1 Run `terraform validate` on all modules
- [ ] 11.4.2 Run `terraform plan` for dev environment
- [ ] 11.4.3 Document estimated costs

---

## PHASE 12: INTEGRATION TESTS & CHAOS ENGINEERING

**Goal**: End-to-end integration tests and chaos engineering.  
**Requirements Covered**: 29, 30

---

### Task 12.1: Create Integration Test Infrastructure
- [ ] 12.1.1 Create `somastack/tests/integration/conftest.py`
  - Testcontainers fixtures for all services
- **Requirements**: 29.1

### Task 12.2: Create Integration Tests
- [ ] 12.2.1 Create `tests/integration/test_event_store.py`
  - Publish, query, replay tests
- [ ] 12.2.2 Create `tests/integration/test_saga.py`
  - Saga execution and compensation tests
- [ ] 12.2.3 Create `tests/integration/test_cross_service.py`
  - SFM → SB → Agent flow tests
- [ ] 12.2.4 Create `tests/integration/test_cognitive_flow.py`
  - Neuromodulation → Adaptation → Sleep cycle tests
- **Requirements**: 29.2, 29.3, 29.4

### Task 12.3: Create Chaos Engineering Tests
- [ ] 12.3.1 Create `tests/chaos/conftest.py`
  - Chaos Mesh / Litmus fixtures
- [ ] 12.3.2 Create `tests/chaos/test_pod_failures.py`
  - Pod failure and recovery tests
- [ ] 12.3.3 Create `tests/chaos/test_network_partitions.py`
  - Network partition tests
- [ ] 12.3.4 Create `tests/chaos/test_kafka_failures.py`
  - Kafka broker failure tests
- [ ] 12.3.5 Create `tests/chaos/test_postgres_failover.py`
  - PostgreSQL failover tests
- [ ] 12.3.6 Create `tests/chaos/test_latency_injection.py`
  - High latency injection tests
- **Requirements**: 30.1, 30.2, 30.3, 30.4

### Task 12.4: FINAL CHECKPOINT - Full System Verification
- [ ] 12.4.1 All unit tests pass
- [ ] 12.4.2 All property tests pass
- [ ] 12.4.3 All integration tests pass
- [ ] 12.4.4 Docker Compose deployment works
- [ ] 12.4.5 Helm chart deployment to local K8s works
- [ ] 12.4.6 Documentation complete and harmonized across all repos
- [ ] 12.4.7 Chaos tests pass in staging environment

---

## Documentation Harmonization Tasks

**Goal**: Ensure consistent documentation across all 4 repositories.

---

### Task DOC.1: SomaFractalMemory Documentation
- [ ] DOC.1.1 Update `somafractalmemory/README.md` with SomaStack section
- [ ] DOC.1.2 Create `somafractalmemory/SOMASTACK.md`
- [ ] DOC.1.3 Update deployment docs for all modes

### Task DOC.2: SomaBrain Documentation
- [ ] DOC.2.1 Update `somabrain/README.md` with SomaStack section
- [ ] DOC.2.2 Create `somabrain/SOMASTACK.md`
- [ ] DOC.2.3 Update deployment docs for all modes
- [ ] DOC.2.4 Document cognitive API endpoints

### Task DOC.3: SomaAgent01 Documentation
- [ ] DOC.3.1 Update `somaAgent01/README.md` with SomaStack section
- [ ] DOC.3.2 Create `somaAgent01/SOMASTACK.md`
- [ ] DOC.3.3 Update deployment docs for all modes
- [ ] DOC.3.4 Document SomaBrain integration

### Task DOC.4: AgentVoiceBox Documentation
- [ ] DOC.4.1 Rewrite `agentVoiceBox/README.md` for voice agent
- [ ] DOC.4.2 Create `agentVoiceBox/SOMASTACK.md`
- [ ] DOC.4.3 Create voice pipeline architecture docs

### Task DOC.5: Cross-Repository Documentation
- [ ] DOC.5.1 Create unified architecture diagram
- [ ] DOC.5.2 Create deployment runbook
- [ ] DOC.5.3 Create troubleshooting guide
- [ ] DOC.5.4 Create API reference for all services

---

## Property-Based Tests Summary

All property tests use `hypothesis` library for property-based testing.

| Test ID | Property | Requirement |
|---------|----------|-------------|
| 8.2.3 | Event Field Completeness | 22.1 |
| 8.3.2 | Atomic Persistence | 22.2 |
| 8.3.3 | Event Ordering Guarantee | 22.5 |
| 8.4.3 | Saga Compensation Order | 23.2 |
| 8.4.4 | Saga State Recovery | 23.3 |
| 8.7.3 | Structured Logging Format | 28.1, 28.2 |
| 8.8.2 | Replay Idempotency | 24.4 |
| 8.9.2 | DLQ Capture and Preservation | 25.1, 25.2 |
| 9.3.1 | Port Range Isolation | 1.3 |
| 9.3.2 | Environment Variable Discovery | 2.4 |

---

## Agentic Implementation Summary

**CRITICAL**: The following tasks implement the core AI/cognitive functionality:

### Neuromodulation System (Task 4.2.2)
- Dopamine: Controls exploration factor and creativity boost (0.0-0.8)
- Serotonin: Controls patience factor and empathy (0.0-1.0)
- Noradrenaline: Controls focus factor and alertness (0.0-0.1)
- Acetylcholine: Controls attention and learning (0.0-0.5)
- Natural decay applied each iteration

### Adaptation State Management (Task 4.2.3)
- Retrieval weights: alpha, beta, gamma, tau
- Utility weights: lambda_, mu, nu
- Learning rate and history tracking
- Feedback-driven weight adjustment

### Sleep Cycles / Memory Consolidation (Task 4.2.4)
- States: active, light, deep, freeze
- Triggered at high cognitive load (>0.8)
- NREM/REM cycle tracking
- Memory pruning and optimization

### Cognitive Thread Management (Task 4.2.6)
- Thread creation per tenant
- Option generation and selection
- Thread reset for clean state

### Cross-Service Cognitive Flow
```
User Input → SomaAgent01 → SomaBrain (Cognitive Processing)
                              ↓
                    Neuromodulation Applied
                              ↓
                    Adaptation Weights Updated
                              ↓
                    Memory Stored (SomaFractalMemory)
                              ↓
                    Response Generated
                              ↓
                    Sleep Cycle (if load > 0.8)
```

---

## Notes

- Tasks marked with `*` are property-based tests (optional but recommended)
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- All configuration files use production-like settings constrained to 15GB RAM
- **NO MOCKS**: All tests use real infrastructure via Testcontainers
- **VIBE Coding Rules**: Enforced throughout - no placeholders, no stubs, no TODOs

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 5.0 | 2025-12-21 | Complete rewrite covering all 32 requirements, agentic implementation |
| 4.0 | 2025-12-20 | Added missing requirements (4, 9, 14, 15, 19, 21, 30, 32) |
| 3.0 | 2025-12-19 | Initial 11-phase structure |

---

**Document Status**: CANONICAL — Single Source of Truth  
**Last Updated**: 2025-12-21  
**Maintained By**: SomaStack Development Team
