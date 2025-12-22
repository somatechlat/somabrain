# Requirements Document

## Introduction

**SomaStack** is a unified, open-source platform for deploying the Soma AI Agent Ecosystem. It provides a "chain reaction" architecture where components (SomaBrain, SomaAgent01, SomaFractalMemory, AgentVoiceBox) work together as specialized organs in an intelligent system, while each can run independently for development.

### Vision

Build the most incredible agentic autonomous platform using 100% open-source technology, deployable from laptop to production with one click.

### Architecture Philosophy

```
🧬 SOMASTACK = The DNA of Autonomous AI Agents

Like a biological system where:
- 🧠 SomaBrain      = Cognitive Processing (thinking, reasoning, learning)
- 🤖 SomaAgent01    = Motor Control (actions, tools, execution)
- 💾 SomaFractalMemory = Hippocampus (memory storage, recall)
- 🎤 AgentVoiceBox  = Sensory Interface (voice input/output)
- ⚡ SomaStack Infra = Nervous System (connecting everything)

Each organ works independently but achieves MORE together!
```

### Technology Stack (100% Open Source)

| Layer | Technology | Purpose | License |
|-------|------------|---------|---------|
| **Event Streaming** | Apache Kafka | Event backbone, durable log | Apache 2.0 |
| **Stream Processing** | Apache Flink | Exactly-once processing, sagas | Apache 2.0 |
| **Workflow Orchestration** | Temporal | Long-running workflows, retries | MIT |
| **API Gateway** | Kong | Rate limiting, auth, routing | Apache 2.0 |
| **Service Mesh** | Linkerd | mTLS, observability, traffic | Apache 2.0 |
| **Database** | PostgreSQL | Canonical state, event store | PostgreSQL |
| **Cache** | Redis | Distributed cache, locks | BSD |
| **Vector Store** | Milvus | Embeddings, similarity search | Apache 2.0 |
| **Object Storage** | MinIO | S3-compatible, checkpoints | AGPL v3 |
| **Schema Registry** | Apicurio | Avro/Protobuf schemas | Apache 2.0 |
| **CDC** | Debezium | Database change capture | Apache 2.0 |
| **Tracing** | Jaeger + OpenTelemetry | Distributed tracing | Apache 2.0 |
| **Metrics** | Prometheus + Grafana | Metrics, dashboards, alerts | Apache 2.0 |
| **Logging** | Loki + Promtail | Log aggregation | AGPL v3 |
| **Policy** | OPA (Open Policy Agent) | Authorization, RBAC | Apache 2.0 |
| **Secrets** | HashiCorp Vault | Secrets management | MPL 2.0 |
| **Certificates** | cert-manager | Automatic TLS | Apache 2.0 |
| **DNS** | ExternalDNS | Automatic DNS records | Apache 2.0 |
| **GitOps** | ArgoCD | Declarative deployments | Apache 2.0 |
| **IaC** | Terraform/OpenTofu | Infrastructure as code | MPL 2.0 |
| **Container Orchestration** | Kubernetes | Production orchestration | Apache 2.0 |
| **Package Manager** | Helm | Kubernetes packaging | Apache 2.0 |

## Glossary

- **SomaStack**: The unified platform providing shared infrastructure for all Soma components
- **Deployment_Mode**: Configuration determining infrastructure topology (standalone/somastack/production)
- **Helm_Umbrella_Chart**: Parent Helm chart that deploys all SomaStack components
- **Service_Mesh**: Network layer providing mTLS, observability, and traffic management
- **GitOps**: Deployment methodology where Git is the source of truth
- **CDC**: Change Data Capture - streaming database changes to Kafka
- **Schema_Registry**: Central repository for event schemas with versioning
- **Saga_Pattern**: Distributed transaction pattern with compensating actions
- **Event_Sourcing**: Storing state changes as immutable events
- **CQRS**: Command Query Responsibility Segregation
- **Idempotency_Key**: Unique key ensuring exactly-once processing
- **Backpressure**: Flow control mechanism when downstream is slow
- **Circuit_Breaker**: Pattern to prevent cascade failures
- **Sidecar**: Container running alongside main container (e.g., Linkerd proxy)

## Requirements

---

### SECTION A: DEPLOYMENT MODES

---

### Requirement 1: Standalone Mode (Developer Laptop)

**User Story:** As a developer, I want to run any Soma component independently on my laptop, so that I can develop and test without the full stack.

#### Acceptance Criteria

1. WHEN SOMA_DEPLOY_MODE=standalone, THE Component SHALL start with its own local Docker Compose infrastructure
2. THE Component SHALL include all required dependencies (Kafka, PostgreSQL, Redis) in its docker-compose.yaml
3. THE Component SHALL use isolated port ranges to avoid conflicts:
   - SomaBrain: 30100-30199
   - SomaAgent01: 20000-20099, 21000-21099
   - SomaFractalMemory: 9500-9599
   - AgentVoiceBox: 25000-25099
4. THE Component SHALL work completely offline without external dependencies
5. THE Component SHALL provide `make dev-up` command for one-command startup
6. WHEN running standalone, THE Component SHALL use local file storage instead of S3/MinIO

### Requirement 2: SomaStack Mode (Integration/Staging)

**User Story:** As a developer, I want to run all Soma components together with shared infrastructure, so that I can test the full "chain reaction" locally.

#### Acceptance Criteria

1. WHEN SOMA_DEPLOY_MODE=somastack, THE Components SHALL connect to shared SomaStack infrastructure
2. THE SomaStack SHALL provide a single docker-compose.yaml that starts all shared infrastructure
3. THE SomaStack SHALL use a shared Docker network `somastack_net` for inter-service communication
4. THE Components SHALL discover shared infrastructure via environment variables:
   - SOMASTACK_KAFKA_BOOTSTRAP=kafka:9092
   - SOMASTACK_POSTGRES_DSN=postgresql://soma:soma@postgres:5432/somastack
   - SOMASTACK_REDIS_URL=redis://redis:6379
   - SOMASTACK_JAEGER_ENDPOINT=http://jaeger:14268
5. THE SomaStack SHALL provide `make somastack-up` command to start everything
6. THE SomaStack SHALL support selective component startup (e.g., only SomaBrain + SomaFractalMemory)
7. THE SomaStack SHALL provide health check dashboard showing all component status

### Requirement 3: Kubernetes Mode (Production-Ready)

**User Story:** As a platform operator, I want to deploy SomaStack to Kubernetes with one click, so that I can run in production with high availability.

#### Acceptance Criteria

1. THE SomaStack SHALL provide Helm umbrella chart `somastack` that deploys all components
2. THE Helm chart SHALL support values override for different environments (dev/staging/prod)
3. THE Helm chart SHALL include all infrastructure components as sub-charts:
   - kafka (Strimzi operator)
   - postgresql (CloudNativePG operator)
   - redis (Redis operator)
   - milvus (Milvus Helm chart)
   - temporal (Temporal Helm chart)
   - flink (Flink Kubernetes operator)
4. THE Helm chart SHALL support both self-managed and cloud-managed infrastructure via feature flags
5. WHEN deploying to AWS, THE Helm chart SHALL support MSK, RDS, ElastiCache via external endpoints
6. THE Helm chart SHALL include Horizontal Pod Autoscaler (HPA) configurations
7. THE Helm chart SHALL include Pod Disruption Budgets (PDB) for high availability
8. THE Helm chart SHALL support multi-zone deployment for fault tolerance

### Requirement 4: Progressive Deployment Pipeline

**User Story:** As a DevOps engineer, I want a clear progression from development to production, so that I can confidently promote changes.

#### Acceptance Criteria

1. THE SomaStack SHALL define deployment levels:
   - Level 0: STANDALONE (laptop, single service)
   - Level 1: SOMASTACK-DEV (all services, Docker Compose)
   - Level 2: SOMASTACK-K8S-LOCAL (minikube/kind)
   - Level 3: SOMASTACK-K8S-STAGING (cloud K8s, test data)
   - Level 4: SOMASTACK-K8S-PROD (production, HA)
2. THE SomaStack SHALL provide promotion scripts between levels
3. THE SomaStack SHALL validate configuration compatibility before promotion
4. THE SomaStack SHALL support canary deployments at Level 3+
5. THE SomaStack SHALL support blue-green deployments at Level 4
6. THE SomaStack SHALL integrate with ArgoCD for GitOps deployments

---

### SECTION B: SHARED INFRASTRUCTURE

---

### Requirement 5: Apache Kafka Event Backbone

**User Story:** As a platform architect, I want a unified event backbone for all services, so that they can communicate asynchronously with guaranteed delivery.

#### Acceptance Criteria

1. THE Kafka cluster SHALL use KRaft mode (no ZooKeeper dependency)
2. THE Kafka cluster SHALL provide topic namespacing by service:
   - `soma.brain.*` - SomaBrain events
   - `soma.agent.*` - SomaAgent01 events
   - `soma.memory.*` - SomaFractalMemory events
   - `soma.voice.*` - AgentVoiceBox events
   - `soma.stack.*` - Cross-service events
3. THE Kafka cluster SHALL enforce schema validation via Schema Registry
4. THE Kafka cluster SHALL support exactly-once semantics (idempotent producers, transactional consumers)
5. THE Kafka cluster SHALL retain events for 7 days (configurable per topic)
6. THE Kafka cluster SHALL support compacted topics for state snapshots
7. WHEN running in Kubernetes, THE Kafka cluster SHALL use Strimzi operator
8. THE Kafka cluster SHALL expose metrics to Prometheus via JMX exporter

### Requirement 6: Apache Flink Stream Processing

**User Story:** As a platform architect, I want exactly-once stream processing for transaction orchestration, so that I never have duplicate or lost events.

#### Acceptance Criteria

1. THE Flink cluster SHALL run in Application Mode for production (one cluster per job)
2. THE Flink cluster SHALL checkpoint to MinIO/S3 every 30 seconds
3. THE Flink cluster SHALL support savepoints for manual replay and upgrades
4. THE Flink cluster SHALL provide jobs for:
   - Transaction saga orchestration
   - Event replay engine
   - Dead letter queue processing
   - Cross-service event routing
5. THE Flink cluster SHALL use RocksDB state backend for large state
6. THE Flink cluster SHALL support event-time processing with watermarks
7. WHEN running in Kubernetes, THE Flink cluster SHALL use Flink Kubernetes Operator
8. THE Flink cluster SHALL expose metrics to Prometheus
9. THE Flink cluster SHALL support PyFlink for Python-based jobs

### Requirement 7: Temporal Workflow Orchestration

**User Story:** As a developer, I want durable workflow execution for long-running operations, so that workflows survive failures and can be retried.

#### Acceptance Criteria

1. THE Temporal cluster SHALL be shared across all Soma components
2. THE Temporal cluster SHALL use PostgreSQL as persistence backend
3. THE Temporal cluster SHALL provide namespace isolation per service:
   - `soma-brain` namespace
   - `soma-agent` namespace
   - `soma-memory` namespace
4. THE Temporal cluster SHALL support workflow versioning for safe deployments
5. THE Temporal cluster SHALL integrate with OpenTelemetry for tracing
6. THE Temporal cluster SHALL provide Web UI for workflow inspection
7. WHEN running in Kubernetes, THE Temporal cluster SHALL use official Helm chart
8. THE Temporal cluster SHALL support Python SDK (temporalio)

### Requirement 8: Kong API Gateway

**User Story:** As a platform operator, I want a unified API gateway for external access, so that I can manage authentication, rate limiting, and routing centrally.

#### Acceptance Criteria

1. THE Kong gateway SHALL route external traffic to internal services
2. THE Kong gateway SHALL provide rate limiting per tenant and per API key
3. THE Kong gateway SHALL integrate with OPA for authorization decisions
4. THE Kong gateway SHALL terminate TLS and provide automatic certificate renewal
5. THE Kong gateway SHALL support request/response transformation
6. THE Kong gateway SHALL provide API analytics and logging
7. THE Kong gateway SHALL support WebSocket proxying for real-time features
8. THE Kong gateway SHALL expose metrics to Prometheus
9. WHEN running in Kubernetes, THE Kong gateway SHALL use Kong Ingress Controller
10. THE Kong gateway SHALL support declarative configuration via decK

### Requirement 9: Linkerd Service Mesh

**User Story:** As a security engineer, I want automatic mTLS between all services, so that internal communication is encrypted and authenticated.

#### Acceptance Criteria

1. THE Linkerd mesh SHALL provide automatic mTLS for all pod-to-pod communication
2. THE Linkerd mesh SHALL inject sidecar proxies automatically via annotation
3. THE Linkerd mesh SHALL provide traffic metrics (latency, success rate, RPS)
4. THE Linkerd mesh SHALL support traffic splitting for canary deployments
5. THE Linkerd mesh SHALL provide retry and timeout policies
6. THE Linkerd mesh SHALL integrate with Prometheus for metrics
7. THE Linkerd mesh SHALL provide Grafana dashboards for service topology
8. THE Linkerd mesh SHALL support multi-cluster communication for geo-distribution

### Requirement 10: PostgreSQL Database Cluster

**User Story:** As a platform operator, I want a highly available PostgreSQL cluster, so that data is durable and services can failover automatically.

#### Acceptance Criteria

1. THE PostgreSQL cluster SHALL use CloudNativePG operator in Kubernetes
2. THE PostgreSQL cluster SHALL support automatic failover with < 30s RTO
3. THE PostgreSQL cluster SHALL provide logical replication for CDC (Debezium)
4. THE PostgreSQL cluster SHALL support connection pooling via PgBouncer
5. THE PostgreSQL cluster SHALL provide automated backups to MinIO/S3
6. THE PostgreSQL cluster SHALL support point-in-time recovery (PITR)
7. THE PostgreSQL cluster SHALL provide separate databases per service:
   - `somabrain` - SomaBrain state
   - `somaagent` - SomaAgent01 state
   - `somamemory` - SomaFractalMemory state
   - `temporal` - Temporal persistence
8. THE PostgreSQL cluster SHALL expose metrics to Prometheus

### Requirement 11: Redis Cache Cluster

**User Story:** As a developer, I want a distributed cache for fast data access and distributed locks, so that services can coordinate and perform efficiently.

#### Acceptance Criteria

1. THE Redis cluster SHALL run in cluster mode for horizontal scaling
2. THE Redis cluster SHALL provide automatic failover with Sentinel
3. THE Redis cluster SHALL support key namespacing per service
4. THE Redis cluster SHALL provide distributed locks via Redlock algorithm
5. THE Redis cluster SHALL support pub/sub for real-time notifications
6. THE Redis cluster SHALL enforce memory limits with LRU eviction
7. THE Redis cluster SHALL persist data with AOF for durability
8. THE Redis cluster SHALL expose metrics to Prometheus

### Requirement 12: Milvus Vector Store

**User Story:** As an AI engineer, I want a scalable vector database for embeddings, so that I can perform fast similarity search across millions of vectors.

#### Acceptance Criteria

1. THE Milvus cluster SHALL support multiple collections per service
2. THE Milvus cluster SHALL use etcd for metadata and MinIO for storage
3. THE Milvus cluster SHALL support IVF_FLAT and HNSW index types
4. THE Milvus cluster SHALL provide automatic index building
5. THE Milvus cluster SHALL support hybrid search (vector + scalar filtering)
6. THE Milvus cluster SHALL scale query nodes independently
7. THE Milvus cluster SHALL expose metrics to Prometheus
8. WHEN running in Kubernetes, THE Milvus cluster SHALL use official Helm chart

### Requirement 13: MinIO Object Storage

**User Story:** As a platform operator, I want S3-compatible object storage, so that I can store checkpoints, backups, and large objects without cloud vendor lock-in.

#### Acceptance Criteria

1. THE MinIO cluster SHALL provide S3-compatible API
2. THE MinIO cluster SHALL run in distributed mode for high availability
3. THE MinIO cluster SHALL provide buckets for:
   - `flink-checkpoints` - Flink state snapshots
   - `postgres-backups` - Database backups
   - `event-archive` - Long-term event storage
   - `model-artifacts` - ML model storage
4. THE MinIO cluster SHALL support bucket versioning
5. THE MinIO cluster SHALL support lifecycle policies for data retention
6. THE MinIO cluster SHALL provide web console for management
7. THE MinIO cluster SHALL expose metrics to Prometheus

### Requirement 14: Apicurio Schema Registry

**User Story:** As a developer, I want centralized schema management for events, so that I can evolve schemas safely without breaking consumers.

#### Acceptance Criteria

1. THE Schema Registry SHALL support Avro, Protobuf, and JSON Schema formats
2. THE Schema Registry SHALL enforce compatibility rules (BACKWARD, FORWARD, FULL)
3. THE Schema Registry SHALL version schemas automatically
4. THE Schema Registry SHALL integrate with Kafka for schema validation
5. THE Schema Registry SHALL provide REST API for schema management
6. THE Schema Registry SHALL support schema groups per service
7. THE Schema Registry SHALL provide web UI for schema browsing
8. THE Schema Registry SHALL store schemas in PostgreSQL

### Requirement 15: Debezium CDC

**User Story:** As a developer, I want database changes streamed to Kafka automatically, so that I can build event-driven systems without dual-write problems.

#### Acceptance Criteria

1. THE Debezium connector SHALL capture changes from PostgreSQL via logical replication
2. THE Debezium connector SHALL publish changes to Kafka topics with schema
3. THE Debezium connector SHALL support table filtering and column masking
4. THE Debezium connector SHALL provide exactly-once delivery with Kafka transactions
5. THE Debezium connector SHALL support snapshot for initial data load
6. THE Debezium connector SHALL handle schema changes gracefully
7. WHEN running in Kubernetes, THE Debezium connector SHALL use Strimzi Kafka Connect
8. THE Debezium connector SHALL expose metrics to Prometheus

---

### SECTION C: OBSERVABILITY

---

### Requirement 16: Distributed Tracing (Jaeger + OpenTelemetry)

**User Story:** As a developer, I want to trace requests across all services, so that I can debug issues and understand system behavior.

#### Acceptance Criteria

1. THE Tracing system SHALL use OpenTelemetry SDK for instrumentation
2. THE Tracing system SHALL propagate W3C Trace Context headers
3. THE Tracing system SHALL auto-instrument HTTP, gRPC, Kafka, and database calls
4. THE Tracing system SHALL export traces to Jaeger collector
5. THE Jaeger backend SHALL store traces in Elasticsearch or Cassandra for production
6. THE Jaeger UI SHALL provide trace search, comparison, and dependency graph
7. THE Tracing system SHALL sample traces intelligently (100% errors, 10% success)
8. THE Tracing system SHALL correlate traces with logs via trace_id

### Requirement 17: Metrics (Prometheus + Grafana)

**User Story:** As an operator, I want comprehensive metrics and dashboards, so that I can monitor system health and set up alerts.

#### Acceptance Criteria

1. THE Prometheus server SHALL scrape metrics from all services via ServiceMonitor
2. THE Prometheus server SHALL retain metrics for 15 days
3. THE Prometheus server SHALL support recording rules for aggregations
4. THE Prometheus server SHALL support alerting rules with AlertManager
5. THE Grafana instance SHALL provide pre-built dashboards for:
   - SomaStack Overview (all services health)
   - Kafka metrics (throughput, lag, partitions)
   - Flink metrics (checkpoints, backpressure, throughput)
   - PostgreSQL metrics (connections, queries, replication)
   - Redis metrics (memory, commands, connections)
   - Service-specific dashboards per component
6. THE Grafana instance SHALL support dashboard-as-code via ConfigMaps
7. THE AlertManager SHALL integrate with PagerDuty, Slack, and email

### Requirement 18: Log Aggregation (Loki + Promtail)

**User Story:** As a developer, I want centralized logs with search and correlation, so that I can debug issues across services.

#### Acceptance Criteria

1. THE Promtail agent SHALL collect logs from all pods automatically
2. THE Promtail agent SHALL enrich logs with Kubernetes metadata (pod, namespace, labels)
3. THE Loki backend SHALL store logs with label-based indexing
4. THE Loki backend SHALL retain logs for 30 days
5. THE Loki backend SHALL support LogQL for querying
6. THE Grafana instance SHALL provide log exploration with trace correlation
7. THE Logging system SHALL enforce structured JSON logging format
8. THE Logging system SHALL support log levels: DEBUG, INFO, WARN, ERROR

---

### SECTION D: SECURITY

---

### Requirement 19: HashiCorp Vault Secrets Management

**User Story:** As a security engineer, I want centralized secrets management with automatic rotation, so that credentials are secure and auditable.

#### Acceptance Criteria

1. THE Vault cluster SHALL store all sensitive credentials (database passwords, API keys)
2. THE Vault cluster SHALL support dynamic secrets for PostgreSQL
3. THE Vault cluster SHALL support Kubernetes auth method for pod authentication
4. THE Vault cluster SHALL provide automatic secret rotation
5. THE Vault cluster SHALL audit all secret access
6. THE Vault Agent Injector SHALL inject secrets into pods as files or env vars
7. THE Vault cluster SHALL support transit encryption for application data
8. THE Vault cluster SHALL use auto-unseal with cloud KMS in production

### Requirement 20: OPA Policy Enforcement

**User Story:** As a security engineer, I want centralized policy enforcement, so that authorization is consistent across all services.

#### Acceptance Criteria

1. THE OPA server SHALL provide policy decisions via REST API
2. THE OPA server SHALL support Rego policy language
3. THE OPA server SHALL integrate with Kong for API authorization
4. THE OPA server SHALL support RBAC and ABAC policies
5. THE OPA server SHALL log all policy decisions for audit
6. THE OPA server SHALL support policy bundles for versioned deployment
7. THE OPA Gatekeeper SHALL enforce Kubernetes admission policies
8. THE OPA server SHALL cache decisions for performance

### Requirement 21: Certificate Management (cert-manager)

**User Story:** As a platform operator, I want automatic TLS certificate management, so that all endpoints are secured without manual intervention.

#### Acceptance Criteria

1. THE cert-manager SHALL issue certificates from Let's Encrypt for public endpoints
2. THE cert-manager SHALL issue certificates from internal CA for service mesh
3. THE cert-manager SHALL automatically renew certificates before expiry
4. THE cert-manager SHALL support DNS-01 challenge for wildcard certificates
5. THE cert-manager SHALL integrate with Kong Ingress for automatic TLS termination
6. THE cert-manager SHALL store certificates in Kubernetes secrets

---

### SECTION E: EVENT SOURCING & TRANSACTIONS

---

### Requirement 22: Event Store

**User Story:** As a developer, I want every state change captured as an immutable event, so that I have complete audit trail and replay capability.

#### Acceptance Criteria

1. WHEN any state-changing operation occurs, THE Event_Store SHALL capture it with:
   - event_id (UUID)
   - trace_id (OpenTelemetry)
   - correlation_id (business transaction)
   - service_id (originating service)
   - tenant_id (multi-tenant isolation)
   - timestamp (event time)
   - event_type (schema name)
   - payload (event data)
   - metadata (additional context)
2. THE Event_Store SHALL persist events to Kafka (streaming) and PostgreSQL (querying) atomically
3. THE Event_Store SHALL use Avro schemas registered in Schema Registry
4. THE Event_Store SHALL support event versioning for schema evolution
5. THE Event_Store SHALL guarantee ordering within partition key

### Requirement 23: Saga Orchestration

**User Story:** As a developer, I want distributed transactions with automatic compensation, so that multi-service operations maintain consistency.

#### Acceptance Criteria

1. THE Saga_Orchestrator SHALL coordinate multi-step transactions across services
2. WHEN a step fails, THE Saga_Orchestrator SHALL execute compensating actions in reverse order
3. THE Saga_Orchestrator SHALL persist saga state in PostgreSQL for crash recovery
4. THE Saga_Orchestrator SHALL support both orchestration and choreography patterns
5. THE Saga_Orchestrator SHALL retry failed steps with exponential backoff
6. IF compensation fails after max retries, THE Saga_Orchestrator SHALL publish to DLQ
7. THE Saga_Orchestrator SHALL be implemented as Flink stateful job

### Requirement 24: Event Replay

**User Story:** As an operator, I want to replay events to rebuild state or debug issues, so that I can recover from failures.

#### Acceptance Criteria

1. THE Replay_Engine SHALL replay events from Kafka in chronological order
2. THE Replay_Engine SHALL support filtering by trace_id, time range, service, event type
3. THE Replay_Engine SHALL use Flink savepoints for point-in-time replay
4. THE Replay_Engine SHALL deduplicate using idempotency keys
5. THE Replay_Engine SHALL use separate consumer group to avoid affecting live processing
6. THE Replay_Engine SHALL provide CLI tool for manual replay operations

### Requirement 25: Dead Letter Queue

**User Story:** As an operator, I want failed events captured for investigation, so that no data is lost and issues can be resolved.

#### Acceptance Criteria

1. THE DLQ SHALL capture events that fail processing after max retries
2. THE DLQ SHALL preserve original event with error details
3. THE DLQ SHALL provide UI for inspecting and replaying failed events
4. THE DLQ SHALL support manual retry with optional transformation
5. THE DLQ SHALL alert operators when events enter DLQ
6. THE DLQ SHALL support automatic retry policies (e.g., retry after 1 hour)

---

### SECTION F: DEVELOPER EXPERIENCE

---

### Requirement 26: Shared Python Library (soma-common)

**User Story:** As a developer, I want reusable primitives for event sourcing and tracing, so that I can easily adopt patterns across services.

#### Acceptance Criteria

1. THE soma-common library SHALL provide:
   - `@trace_transaction` decorator for automatic tracing
   - `@with_compensation(action)` decorator for saga steps
   - `EventStore` class for publishing/querying events
   - `SagaOrchestrator` class for saga management
   - `TransactionScope` context manager for boundaries
2. THE soma-common library SHALL auto-configure based on SOMA_DEPLOY_MODE
3. THE soma-common library SHALL be published to private PyPI (or Git submodule)
4. THE soma-common library SHALL provide type hints and documentation
5. THE soma-common library SHALL include pytest fixtures for testing

### Requirement 27: CLI Tools

**User Story:** As a developer, I want CLI tools for common operations, so that I can manage the platform efficiently.

#### Acceptance Criteria

1. THE somastack CLI SHALL provide commands:
   - `somastack up [--mode standalone|somastack|k8s]` - Start platform
   - `somastack down` - Stop platform
   - `somastack status` - Show component health
   - `somastack logs [service]` - Tail logs
   - `somastack events list [--trace-id X]` - Query events
   - `somastack events replay [--from TIME]` - Replay events
   - `somastack saga list` - List active sagas
   - `somastack saga inspect [saga-id]` - Show saga details
   - `somastack dlq list` - List DLQ events
   - `somastack dlq retry [event-id]` - Retry DLQ event
2. THE somastack CLI SHALL be installable via pip
3. THE somastack CLI SHALL support shell completion

### Requirement 28: Beautiful Logging

**User Story:** As a developer, I want clear, beautiful logs that tell the story of each transaction, so that I can quickly understand system behavior.

#### Acceptance Criteria

1. THE Logging system SHALL use structured JSON with consistent fields:
   - timestamp, level, service, trace_id, correlation_id, tenant_id, message, data
2. THE Logging system SHALL use emoji indicators:
   - ✅ SUCCESS, ❌ ERROR, ⚠️ WARNING, ℹ️ INFO, 🔍 DEBUG
   - 🧠 COGNITIVE, 🤖 AGENT, 💾 MEMORY, 🎤 VOICE
   - 🔄 IN_PROGRESS, ⏱️ TIMING, 🔗 TRACE
3. THE Logging system SHALL format nested data for readability
4. THE Logging system SHALL truncate large payloads with "[truncated]"
5. THE Logging system SHALL use colors in terminal output
6. THE Logging system SHALL correlate logs across services via trace_id

---

### SECTION G: TESTING & QUALITY

---

### Requirement 29: Integration Testing

**User Story:** As a developer, I want automated integration tests against real infrastructure, so that I can verify the system works end-to-end.

#### Acceptance Criteria

1. THE Test suite SHALL use Testcontainers for spinning up real infrastructure
2. THE Test suite SHALL support event replay for deterministic testing
3. THE Test suite SHALL verify saga compensation works correctly
4. THE Test suite SHALL test cross-service communication
5. THE Test suite SHALL run in CI/CD pipeline
6. THE Test suite SHALL provide coverage reports

### Requirement 30: Chaos Engineering

**User Story:** As an SRE, I want to test system resilience under failure conditions, so that I can ensure high availability.

#### Acceptance Criteria

1. THE Chaos tests SHALL use Chaos Mesh or Litmus for Kubernetes
2. THE Chaos tests SHALL simulate:
   - Pod failures
   - Network partitions
   - Kafka broker failures
   - PostgreSQL failover
   - High latency injection
3. THE Chaos tests SHALL verify system recovers automatically
4. THE Chaos tests SHALL verify no data loss during failures
5. THE Chaos tests SHALL run in staging environment on schedule

---

### SECTION H: CLOUD DEPLOYMENT

---

### Requirement 31: AWS Production Deployment

**User Story:** As a platform operator, I want to deploy SomaStack to AWS with managed services, so that I get enterprise-grade reliability.

#### Acceptance Criteria

1. THE Terraform modules SHALL provision:
   - EKS cluster with managed node groups
   - MSK (Managed Kafka) cluster
   - RDS PostgreSQL with Multi-AZ
   - ElastiCache Redis cluster
   - S3 buckets for storage
   - Route 53 for DNS
   - ACM for certificates
   - CloudWatch for AWS-native monitoring
2. THE Helm charts SHALL support external endpoints for managed services
3. THE deployment SHALL use separate AWS accounts for staging/production
4. THE deployment SHALL use IAM roles for service accounts (IRSA)
5. THE deployment SHALL enable VPC endpoints for AWS services

### Requirement 32: Multi-Region / Disaster Recovery

**User Story:** As a platform operator, I want multi-region deployment capability, so that I can achieve high availability and disaster recovery.

#### Acceptance Criteria

1. THE Architecture SHALL support active-passive multi-region deployment
2. THE Kafka cluster SHALL support MirrorMaker 2 for cross-region replication
3. THE PostgreSQL cluster SHALL support cross-region read replicas
4. THE deployment SHALL support < 1 hour RTO for region failover
5. THE deployment SHALL support < 15 minute RPO for data loss
6. THE deployment SHALL provide runbooks for failover procedures
