# Design Document: SomaStack Platform

## Overview

SomaStack is a unified, open-source platform for deploying the Soma AI Agent Ecosystem. This design document describes the architecture, components, and implementation details for building a production-grade, highly available platform that enables the "chain reaction" of intelligent components.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    🌐 EXTERNAL TRAFFIC                                   │
└─────────────────────────────────────────────┬───────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              🦍 KONG API GATEWAY                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                    │
│  │ Rate Limit  │  │    Auth     │  │   Routing   │  │  Analytics  │                    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                    │
└─────────────────────────────────────────────┬───────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              🔗 LINKERD SERVICE MESH                                     │
│                         (mTLS, Traffic Management, Observability)                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                    │                         │                         │
                    ▼                         ▼                         ▼
```

### Soma Components Layer

```
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   🧠 SOMABRAIN    │  │  🤖 SOMAAGENT01   │  │ 💾 SOMAFRACTAL    │  │  🎤 VOICEBOX      │
│                   │  │                   │  │    MEMORY         │  │                   │
│ • Cognitive API   │  │ • Gateway         │  │ • Memory API      │  │ • Voice API       │
│ • Sleep System    │  │ • Conv Worker     │  │ • Vector Store    │  │ • STT/TTS         │
│ • Neuromod        │  │ • Tool Executor   │  │ • Graph Store     │  │ • WebSocket       │
│ • Adaptation      │  │ • Memory Repl     │  │ • KV Store        │  │                   │
│                   │  │ • FastA2A         │  │                   │  │                   │
│ Port: 9696        │  │ Port: 21016       │  │ Port: 9595        │  │ Port: 25000       │
│ RAM: 2GB          │  │ RAM: 2GB          │  │ RAM: 1GB          │  │ RAM: 512MB        │
└─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
          │                      │                      │                      │
          └──────────────────────┴──────────┬───────────┴──────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           ⚡ SOMASTACK SHARED INFRASTRUCTURE                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Infrastructure Layer

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              📨 EVENT STREAMING LAYER                                    │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐      │
│  │         Apache Kafka (KRaft)        │  │       Apache Flink (Session)        │      │
│  │  • 3 partitions per topic           │  │  • Saga Orchestrator Job            │      │
│  │  • 7 day retention                  │  │  • Event Replay Job                 │      │
│  │  • Snappy compression               │  │  • DLQ Processor Job                │      │
│  │  • Exactly-once semantics           │  │  • 30s checkpoints to MinIO         │      │
│  │  Port: 9092 (internal), 9094 (ext)  │  │  Port: 8081 (UI)                    │      │
│  │  RAM: 1.5GB                         │  │  RAM: 1.5GB                         │      │
│  └─────────────────────────────────────┘  └─────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              🔄 WORKFLOW & GATEWAY LAYER                                 │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐      │
│  │           Temporal                  │  │            Kong Gateway             │      │
│  │  • Workflow orchestration           │  │  • API routing                      │      │
│  │  • Durable execution                │  │  • Rate limiting                    │      │
│  │  • PostgreSQL backend               │  │  • Authentication                   │      │
│  │  Port: 7233 (gRPC), 8080 (UI)       │  │  Port: 8000 (proxy), 8001 (admin)   │      │
│  │  RAM: 1GB                           │  │  RAM: 512MB                         │      │
│  └─────────────────────────────────────┘  └─────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              💾 DATA LAYER                                               │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐                   │
│  │    PostgreSQL     │  │      Redis        │  │      Milvus       │                   │
│  │  • Event store    │  │  • Cache          │  │  • Vectors        │                   │
│  │  • Saga state     │  │  • Locks          │  │  • Embeddings     │                   │
│  │  • All services   │  │  • Pub/Sub        │  │  • Similarity     │                   │
│  │  Port: 5432       │  │  Port: 6379       │  │  Port: 19530      │                   │
│  │  RAM: 1GB         │  │  RAM: 512MB       │  │  RAM: 2GB         │                   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘                   │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐                   │
│  │      MinIO        │  │      etcd         │  │  Schema Registry  │                   │
│  │  • Checkpoints    │  │  • Milvus meta    │  │  • Avro schemas   │                   │
│  │  • Backups        │  │  • Coordination   │  │  • Versioning     │                   │
│  │  Port: 9000/9001  │  │  Port: 2379       │  │  Port: 8081       │                   │
│  │  RAM: 512MB       │  │  RAM: 256MB       │  │  RAM: 256MB       │                   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              📊 OBSERVABILITY LAYER                                      │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐                   │
│  │      Jaeger       │  │    Prometheus     │  │     Grafana       │                   │
│  │  • Tracing        │  │  • Metrics        │  │  • Dashboards     │                   │
│  │  Port: 16686      │  │  Port: 9090       │  │  Port: 3000       │                   │
│  │  RAM: 256MB       │  │  RAM: 512MB       │  │  RAM: 256MB       │                   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘                   │
│  ┌───────────────────┐  ┌───────────────────┐                                          │
│  │       Loki        │  │       OPA         │                                          │
│  │  • Log aggregation│  │  • Policies       │                                          │
│  │  Port: 3100       │  │  Port: 8181       │                                          │
│  │  RAM: 256MB       │  │  RAM: 128MB       │                                          │
│  └───────────────────┘  └───────────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Resource Allocation (15GB Total)

### Memory Budget

| Component | RAM Limit | RAM Reserved | Purpose |
|-----------|-----------|--------------|---------|
| **Soma Services** | | | |
| SomaBrain | 2.0 GB | 1.0 GB | Cognitive processing |
| SomaAgent01 | 2.0 GB | 1.0 GB | Agent orchestration |
| SomaFractalMemory | 1.0 GB | 512 MB | Memory service |
| AgentVoiceBox | 512 MB | 256 MB | Voice interface |
| **Event Streaming** | | | |
| Kafka | 1.5 GB | 768 MB | Event backbone |
| Flink JobManager | 512 MB | 256 MB | Job coordination |
| Flink TaskManager | 1.0 GB | 512 MB | Stream processing |
| **Workflow** | | | |
| Temporal | 1.0 GB | 512 MB | Workflow engine |
| Kong | 512 MB | 256 MB | API gateway |
| **Data Stores** | | | |
| PostgreSQL | 1.0 GB | 512 MB | Relational data |
| Redis | 512 MB | 256 MB | Cache & locks |
| Milvus | 2.0 GB | 1.0 GB | Vector store |
| MinIO | 512 MB | 256 MB | Object storage |
| etcd | 256 MB | 128 MB | Milvus metadata |
| Schema Registry | 256 MB | 128 MB | Event schemas |
| **Observability** | | | |
| Jaeger | 256 MB | 128 MB | Tracing |
| Prometheus | 512 MB | 256 MB | Metrics |
| Grafana | 256 MB | 128 MB | Dashboards |
| Loki | 256 MB | 128 MB | Logs |
| OPA | 128 MB | 64 MB | Policies |
| **TOTAL** | **15.0 GB** | **8.0 GB** | |


## Components and Interfaces

### 1. Event Store Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

class EventType(str, Enum):
    """Standard event types across SomaStack."""
    # Transaction events
    TRANSACTION_STARTED = "txn.started"
    TRANSACTION_COMMITTED = "txn.committed"
    TRANSACTION_FAILED = "txn.failed"
    TRANSACTION_COMPENSATING = "txn.compensating"
    TRANSACTION_ROLLED_BACK = "txn.rolled_back"
    
    # Saga events
    SAGA_STARTED = "saga.started"
    SAGA_STEP_COMPLETED = "saga.step.completed"
    SAGA_STEP_FAILED = "saga.step.failed"
    SAGA_COMPLETED = "saga.completed"
    SAGA_COMPENSATING = "saga.compensating"
    
    # Service-specific (examples)
    MEMORY_STORED = "memory.stored"
    MEMORY_RECALLED = "memory.recalled"
    AGENT_TASK_STARTED = "agent.task.started"
    AGENT_TASK_COMPLETED = "agent.task.completed"
    COGNITIVE_STATE_CHANGED = "cognitive.state.changed"

@dataclass
class Event:
    """Immutable event for event sourcing."""
    event_id: str                    # UUID
    event_type: EventType            # Schema type
    trace_id: str                    # OpenTelemetry trace
    correlation_id: str              # Business transaction
    service_id: str                  # Originating service
    tenant_id: str                   # Multi-tenant isolation
    timestamp: datetime              # Event time (not processing time)
    payload: Dict[str, Any]          # Event data
    metadata: Dict[str, Any]         # Additional context
    schema_version: str = "1.0"      # For evolution

class IEventStore(ABC):
    """Interface for event store operations."""
    
    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """Publish event to Kafka and PostgreSQL atomically."""
        pass
    
    @abstractmethod
    async def query(
        self,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        service_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Query events from PostgreSQL."""
        pass
    
    @abstractmethod
    async def replay(
        self,
        trace_id: str,
        handler: callable,
    ) -> int:
        """Replay events for a trace ID."""
        pass
```

### 2. Saga Orchestrator Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, List, Optional
from enum import Enum

class SagaStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class SagaStep:
    """A single step in a saga with its compensation."""
    name: str
    action: Callable                 # Forward action
    compensation: Callable           # Rollback action
    timeout_seconds: int = 30
    max_retries: int = 3

@dataclass
class Saga:
    """Distributed transaction as a sequence of steps."""
    saga_id: str
    trace_id: str
    correlation_id: str
    tenant_id: str
    steps: List[SagaStep]
    status: SagaStatus = SagaStatus.PENDING
    current_step: int = 0
    completed_steps: List[str] = field(default_factory=list)
    error: Optional[str] = None

class ISagaOrchestrator(ABC):
    """Interface for saga orchestration."""
    
    @abstractmethod
    async def start_saga(self, saga: Saga) -> str:
        """Start a new saga, returns saga_id."""
        pass
    
    @abstractmethod
    async def get_saga(self, saga_id: str) -> Optional[Saga]:
        """Get saga by ID."""
        pass
    
    @abstractmethod
    async def compensate(self, saga_id: str) -> bool:
        """Trigger compensation for a saga."""
        pass
```

### 3. Transaction Tracer Interface

```python
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class TraceContext:
    """OpenTelemetry trace context."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service_id: str
    tenant_id: str
    correlation_id: str
    baggage: Dict[str, str]

class ITransactionTracer(ABC):
    """Interface for distributed tracing."""
    
    @abstractmethod
    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Start a new span within current trace."""
        yield
    
    @abstractmethod
    def get_current_context(self) -> TraceContext:
        """Get current trace context."""
        pass
    
    @abstractmethod
    def inject_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into outgoing headers."""
        pass
    
    @abstractmethod
    def extract_context(self, headers: Dict[str, str]) -> TraceContext:
        """Extract trace context from incoming headers."""
        pass
```


## Data Models

### Event Store Schema (PostgreSQL)

```sql
-- Events table (append-only)
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(64) NOT NULL,
    service_id VARCHAR(50) NOT NULL,
    tenant_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    schema_version VARCHAR(10) DEFAULT '1.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for common queries
    INDEX idx_events_trace_id (trace_id),
    INDEX idx_events_correlation_id (correlation_id),
    INDEX idx_events_tenant_service (tenant_id, service_id),
    INDEX idx_events_type_timestamp (event_type, timestamp),
    INDEX idx_events_timestamp (timestamp)
);

-- Partitioning by month for scalability
CREATE TABLE events_2025_01 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Saga state table
CREATE TABLE sagas (
    saga_id UUID PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    current_step INT DEFAULT 0,
    steps JSONB NOT NULL,
    completed_steps JSONB DEFAULT '[]',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_sagas_trace_id (trace_id),
    INDEX idx_sagas_tenant_status (tenant_id, status)
);

-- Idempotency keys for exactly-once processing
CREATE TABLE idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Outbox table for transactional messaging
CREATE TABLE outbox (
    id BIGSERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    key VARCHAR(255),
    payload JSONB NOT NULL,
    headers JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending',
    retries INT DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    
    INDEX idx_outbox_status (status, created_at)
);
```

### Kafka Topics

```yaml
# Topic naming convention: soma.<service>.<domain>.<event-type>
topics:
  # Cross-service transaction events
  - name: soma.stack.txn.events
    partitions: 6
    replication: 1  # 3 in production
    retention_ms: 604800000  # 7 days
    cleanup_policy: delete
    
  # Saga orchestration
  - name: soma.stack.saga.commands
    partitions: 6
    replication: 1
    retention_ms: 86400000  # 1 day
    
  - name: soma.stack.saga.events
    partitions: 6
    replication: 1
    retention_ms: 604800000
    
  # Dead letter queue
  - name: soma.stack.dlq
    partitions: 3
    replication: 1
    retention_ms: 2592000000  # 30 days
    
  # Service-specific topics
  - name: soma.brain.cognitive.events
    partitions: 3
    replication: 1
    
  - name: soma.agent.task.events
    partitions: 6
    replication: 1
    
  - name: soma.memory.store.events
    partitions: 3
    replication: 1
    
  # CDC topics (Debezium)
  - name: soma.cdc.postgres.events
    partitions: 3
    replication: 1
    cleanup_policy: compact
```

### Avro Schemas (Schema Registry)

```json
{
  "type": "record",
  "name": "SomaEvent",
  "namespace": "com.soma.events",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "event_type", "type": "string"},
    {"name": "trace_id", "type": "string"},
    {"name": "correlation_id", "type": "string"},
    {"name": "service_id", "type": "string"},
    {"name": "tenant_id", "type": "string"},
    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "payload", "type": "string"},  // JSON string
    {"name": "metadata", "type": ["null", "string"], "default": null},
    {"name": "schema_version", "type": "string", "default": "1.0"}
  ]
}
```


## Deployment Configuration

### Docker Compose (SomaStack Mode - 15GB RAM) - PRODUCTION-LIKE

```yaml
# somastack/docker-compose.yaml
# ============================================================================
# SOMASTACK UNIFIED PLATFORM - PRODUCTION-LIKE LOCAL DEPLOYMENT
# Total RAM Budget: 15GB | All settings production-grade but resource-constrained
# ============================================================================
name: somastack

# ============================================================================
# SHARED CONFIGURATIONS (YAML Anchors)
# ============================================================================

x-logging: &default-logging
  driver: json-file
  options:
    max-size: "50m"
    max-file: "5"
    compress: "true"
    labels: "service,environment"

x-healthcheck-defaults: &healthcheck-defaults
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s

x-restart-policy: &restart-policy
  restart: unless-stopped

x-security-opts: &security-opts
  security_opt:
    - no-new-privileges:true

x-common-labels: &common-labels
  labels:
    - "com.somastack.environment=local"
    - "com.somastack.version=1.0.0"
    - "com.somastack.managed=true"

services:
  # ============================================================================
  # 📨 EVENT STREAMING LAYER
  # ============================================================================
  
  kafka:
    image: apache/kafka:3.7.0
    container_name: somastack_kafka
    hostname: kafka
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # KRaft Mode (No Zookeeper)
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      CLUSTER_ID: "SomaStackKafkaCluster01"
      
      # Listeners - Production-like multi-listener setup
      KAFKA_LISTENERS: INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9094,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: INTERNAL://kafka:9092,EXTERNAL://localhost:9094
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      
      # Topic Defaults - Production settings
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_NUM_PARTITIONS: 6
      KAFKA_DEFAULT_REPLICATION_FACTOR: 1  # 3 in production
      KAFKA_MIN_INSYNC_REPLICAS: 1         # 2 in production
      
      # Log Retention - 7 days
      KAFKA_LOG_RETENTION_HOURS: 168
      KAFKA_LOG_RETENTION_BYTES: 10737418240  # 10GB per partition
      KAFKA_LOG_SEGMENT_BYTES: 1073741824     # 1GB segments
      KAFKA_LOG_CLEANUP_POLICY: delete
      
      # Performance Tuning
      KAFKA_COMPRESSION_TYPE: snappy
      KAFKA_BATCH_SIZE: 65536
      KAFKA_LINGER_MS: 5
      KAFKA_BUFFER_MEMORY: 67108864
      KAFKA_MAX_REQUEST_SIZE: 10485760
      
      # Exactly-Once Semantics
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTIONAL_ID_EXPIRATION_MS: 604800000
      
      # Consumer Settings
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 3000
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      
      # JVM Settings - Optimized for 1.5GB limit
      KAFKA_HEAP_OPTS: "-Xms512m -Xmx1g -XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35"
      KAFKA_JVM_PERFORMANCE_OPTS: "-XX:+ExplicitGCInvokesConcurrent -Djava.awt.headless=true"
      
      # Metrics
      KAFKA_JMX_PORT: 9999
      KAFKA_JMX_HOSTNAME: kafka
    ports:
      - "9094:9094"   # External clients
      - "9999:9999"   # JMX metrics
    volumes:
      - kafka_data:/var/lib/kafka/data
      - kafka_logs:/var/lib/kafka/logs
      - ./config/kafka/server.properties:/opt/kafka/config/kraft/server.properties:ro
    deploy:
      resources:
        limits:
          memory: 1536M
          cpus: "2.0"
        reservations:
          memory: 768M
          cpus: "0.5"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "kafka-broker-api-versions.sh --bootstrap-server localhost:9092 || exit 1"]
      start_period: 90s
    networks:
      somastack_net:
        aliases:
          - kafka
          - kafka.somastack.local
    logging: *default-logging
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
      memlock:
        soft: -1
        hard: -1

  # --------------------------------------------------------------------------
  # Apache Flink - Stream Processing Engine
  # --------------------------------------------------------------------------
  
  flink-jobmanager:
    image: flink:1.18-java11
    container_name: somastack_flink_jm
    hostname: flink-jobmanager
    <<: [*restart-policy, *security-opts, *common-labels]
    command: jobmanager
    environment:
      # Flink Configuration
      FLINK_PROPERTIES: |
        # JobManager Settings
        jobmanager.rpc.address: flink-jobmanager
        jobmanager.rpc.port: 6123
        jobmanager.memory.process.size: 512m
        jobmanager.memory.heap.size: 384m
        jobmanager.memory.off-heap.size: 128m
        
        # High Availability (disabled for local, enable in prod)
        # high-availability: zookeeper
        # high-availability.storageDir: s3://flink-ha/
        
        # State Backend - RocksDB for production-like behavior
        state.backend: rocksdb
        state.backend.rocksdb.memory.managed: true
        state.backend.rocksdb.memory.fixed-per-slot: 64mb
        state.backend.incremental: true
        
        # Checkpointing - Production settings
        state.checkpoints.dir: s3://flink-checkpoints/checkpoints
        state.savepoints.dir: s3://flink-checkpoints/savepoints
        execution.checkpointing.interval: 30s
        execution.checkpointing.mode: EXACTLY_ONCE
        execution.checkpointing.timeout: 10min
        execution.checkpointing.min-pause: 10s
        execution.checkpointing.max-concurrent-checkpoints: 1
        execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION
        
        # S3 Configuration (MinIO)
        s3.endpoint: http://minio:9000
        s3.access-key: minioadmin
        s3.secret-key: minioadmin
        s3.path.style.access: true
        
        # Web UI
        web.submit.enable: true
        web.cancel.enable: true
        web.upload.dir: /opt/flink/uploads
        
        # Metrics
        metrics.reporters: prometheus
        metrics.reporter.prometheus.factory.class: org.apache.flink.metrics.prometheus.PrometheusReporterFactory
        metrics.reporter.prometheus.port: 9249
        
        # Restart Strategy
        restart-strategy: exponential-delay
        restart-strategy.exponential-delay.initial-backoff: 1s
        restart-strategy.exponential-delay.max-backoff: 60s
        restart-strategy.exponential-delay.backoff-multiplier: 2.0
        restart-strategy.exponential-delay.reset-backoff-threshold: 10min
        restart-strategy.exponential-delay.jitter-factor: 0.1
    ports:
      - "8081:8081"   # Web UI
      - "6123:6123"   # RPC
      - "9249:9249"   # Prometheus metrics
    volumes:
      - flink_checkpoints:/opt/flink/checkpoints
      - flink_savepoints:/opt/flink/savepoints
      - flink_uploads:/opt/flink/uploads
      - ./config/flink/flink-conf.yaml:/opt/flink/conf/flink-conf.yaml:ro
      - ./config/flink/log4j-console.properties:/opt/flink/conf/log4j-console.properties:ro
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.25"
    depends_on:
      kafka:
        condition: service_healthy
      minio:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -sf http://localhost:8081/overview || exit 1"]
      start_period: 120s
    networks:
      somastack_net:
        aliases:
          - flink-jobmanager
          - flink.somastack.local
    logging: *default-logging

  flink-taskmanager:
    image: flink:1.18-java11
    container_name: somastack_flink_tm
    hostname: flink-taskmanager
    <<: [*restart-policy, *security-opts, *common-labels]
    command: taskmanager
    environment:
      FLINK_PROPERTIES: |
        # TaskManager Settings
        jobmanager.rpc.address: flink-jobmanager
        taskmanager.memory.process.size: 1g
        taskmanager.memory.flink.size: 768m
        taskmanager.memory.managed.fraction: 0.4
        taskmanager.memory.network.fraction: 0.1
        taskmanager.numberOfTaskSlots: 4
        
        # State Backend
        state.backend: rocksdb
        state.backend.rocksdb.memory.managed: true
        state.backend.rocksdb.memory.fixed-per-slot: 64mb
        state.backend.incremental: true
        
        # S3 Configuration
        s3.endpoint: http://minio:9000
        s3.access-key: minioadmin
        s3.secret-key: minioadmin
        s3.path.style.access: true
        
        # Network
        taskmanager.network.memory.fraction: 0.1
        taskmanager.network.memory.min: 64mb
        taskmanager.network.memory.max: 128mb
        
        # Metrics
        metrics.reporters: prometheus
        metrics.reporter.prometheus.factory.class: org.apache.flink.metrics.prometheus.PrometheusReporterFactory
        metrics.reporter.prometheus.port: 9249
    volumes:
      - flink_tm_data:/opt/flink/data
      - ./config/flink/flink-conf.yaml:/opt/flink/conf/flink-conf.yaml:ro
      - ./config/flink/log4j-console.properties:/opt/flink/conf/log4j-console.properties:ro
    deploy:
      resources:
        limits:
          memory: 1024M
          cpus: "2.0"
        reservations:
          memory: 512M
          cpus: "0.5"
    depends_on:
      flink-jobmanager:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -sf http://localhost:9249/metrics || exit 1"]
      start_period: 90s
    networks:
      - somastack_net
    logging: *default-logging

  # ============================================================================
  # 🔄 WORKFLOW & GATEWAY LAYER
  # ============================================================================
  
  # --------------------------------------------------------------------------
  # Temporal - Workflow Orchestration Engine
  # --------------------------------------------------------------------------
  
  temporal:
    image: temporalio/auto-setup:1.23
    container_name: somastack_temporal
    hostname: temporal
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Database Configuration
      DB: postgresql
      DB_PORT: 5432
      POSTGRES_USER: soma
      POSTGRES_PWD: soma
      POSTGRES_SEEDS: postgres
      
      # Temporal Server Settings
      TEMPORAL_ADDRESS: temporal:7233
      TEMPORAL_CLI_ADDRESS: temporal:7233
      
      # Namespace Configuration
      DEFAULT_NAMESPACE: somastack
      DEFAULT_NAMESPACE_RETENTION: 72h
      
      # Dynamic Config
      DYNAMIC_CONFIG_FILE_PATH: /etc/temporal/dynamicconfig.yaml
      
      # Logging
      LOG_LEVEL: info
      
      # Performance Tuning
      FRONTEND_GRPC_MAX_MESSAGE_SIZE: 4194304
      HISTORY_GRPC_MAX_MESSAGE_SIZE: 4194304
      
      # Metrics
      PROMETHEUS_ENDPOINT: 0.0.0.0:9090
    ports:
      - "7233:7233"   # gRPC Frontend
      - "7234:7234"   # gRPC History
      - "7235:7235"   # gRPC Matching
      - "7239:7239"   # gRPC Worker
      - "9090:9090"   # Prometheus metrics
    volumes:
      - ./config/temporal/dynamicconfig.yaml:/etc/temporal/dynamicconfig.yaml:ro
      - ./config/temporal/development.yaml:/etc/temporal/config/development.yaml:ro
      - temporal_data:/var/lib/temporal
    deploy:
      resources:
        limits:
          memory: 1024M
          cpus: "2.0"
        reservations:
          memory: 512M
          cpus: "0.5"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "temporal", "operator", "cluster", "health"]
      start_period: 120s
    networks:
      somastack_net:
        aliases:
          - temporal
          - temporal.somastack.local
    logging: *default-logging

  temporal-ui:
    image: temporalio/ui:2.26
    container_name: somastack_temporal_ui
    hostname: temporal-ui
    <<: [*restart-policy, *common-labels]
    environment:
      TEMPORAL_ADDRESS: temporal:7233
      TEMPORAL_CORS_ORIGINS: http://localhost:3000,http://localhost:8080
      TEMPORAL_UI_PORT: 8080
      TEMPORAL_NOTIFY_ON_NEW_VERSION: "false"
      TEMPORAL_FEEDBACK_URL: ""
      TEMPORAL_CODEC_ENDPOINT: ""
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.5"
        reservations:
          memory: 64M
          cpus: "0.1"
    depends_on:
      temporal:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "wget -q --spider http://localhost:8080 || exit 1"]
    networks:
      - somastack_net
    logging: *default-logging

  temporal-admin-tools:
    image: temporalio/admin-tools:1.23
    container_name: somastack_temporal_admin
    hostname: temporal-admin
    <<: [*common-labels]
    environment:
      TEMPORAL_ADDRESS: temporal:7233
      TEMPORAL_CLI_ADDRESS: temporal:7233
    depends_on:
      temporal:
        condition: service_healthy
    networks:
      - somastack_net
    stdin_open: true
    tty: true
    profiles:
      - tools

  # --------------------------------------------------------------------------
  # Kong - API Gateway
  # --------------------------------------------------------------------------
  
  kong:
    image: kong:3.6-alpine
    container_name: somastack_kong
    hostname: kong
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Database-less mode (declarative config)
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /etc/kong/kong.yaml
      
      # Proxy Settings
      KONG_PROXY_LISTEN: 0.0.0.0:8000, 0.0.0.0:8443 ssl
      KONG_ADMIN_LISTEN: 0.0.0.0:8001, 0.0.0.0:8444 ssl
      
      # Logging
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_LOG_LEVEL: info
      
      # Performance
      KONG_NGINX_WORKER_PROCESSES: auto
      KONG_UPSTREAM_KEEPALIVE_POOL_SIZE: 60
      KONG_UPSTREAM_KEEPALIVE_MAX_REQUESTS: 1000
      KONG_UPSTREAM_KEEPALIVE_IDLE_TIMEOUT: 60
      
      # Plugins
      KONG_PLUGINS: bundled,prometheus
      
      # SSL/TLS (self-signed for local)
      KONG_SSL_CERT: /etc/kong/ssl/kong.crt
      KONG_SSL_CERT_KEY: /etc/kong/ssl/kong.key
      
      # Tracing
      KONG_TRACING_INSTRUMENTATIONS: all
      KONG_TRACING_SAMPLING_RATE: 1.0
      
      # DNS
      KONG_DNS_RESOLVER: 127.0.0.11
      KONG_DNS_ORDER: LAST,A,CNAME
    ports:
      - "8000:8000"   # HTTP Proxy
      - "8443:8443"   # HTTPS Proxy
      - "8001:8001"   # Admin API HTTP
      - "8444:8444"   # Admin API HTTPS
    volumes:
      - ./config/kong/kong.yaml:/etc/kong/kong.yaml:ro
      - ./config/kong/ssl:/etc/kong/ssl:ro
      - kong_prefix:/var/run/kong
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.25"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "kong", "health"]
    networks:
      somastack_net:
        aliases:
          - kong
          - api.somastack.local
    logging: *default-logging

  # ============================================================================
  # 💾 DATA LAYER
  # ============================================================================
  
  # --------------------------------------------------------------------------
  # PostgreSQL - Primary Database
  # --------------------------------------------------------------------------
  
  postgres:
    image: postgres:16-alpine
    container_name: somastack_postgres
    hostname: postgres
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Authentication
      POSTGRES_USER: soma
      POSTGRES_PASSWORD: soma
      POSTGRES_DB: somastack
      
      # Data Directory
      PGDATA: /var/lib/postgresql/data/pgdata
      
      # Initialization
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./config/postgres/init:/docker-entrypoint-initdb.d:ro
      - ./config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./config/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
      - postgres_backups:/backups
    command:
      - postgres
      - -c
      - config_file=/etc/postgresql/postgresql.conf
      - -c
      - hba_file=/etc/postgresql/pg_hba.conf
      # Connection Settings
      - -c
      - max_connections=200
      - -c
      - superuser_reserved_connections=3
      # Memory Settings (optimized for 1GB limit)
      - -c
      - shared_buffers=256MB
      - -c
      - effective_cache_size=512MB
      - -c
      - work_mem=4MB
      - -c
      - maintenance_work_mem=64MB
      # WAL Settings (for CDC/Debezium)
      - -c
      - wal_level=logical
      - -c
      - max_wal_senders=10
      - -c
      - max_replication_slots=10
      - -c
      - wal_keep_size=1GB
      # Checkpoint Settings
      - -c
      - checkpoint_completion_target=0.9
      - -c
      - checkpoint_timeout=10min
      - -c
      - max_wal_size=2GB
      - -c
      - min_wal_size=512MB
      # Query Planner
      - -c
      - random_page_cost=1.1
      - -c
      - effective_io_concurrency=200
      # Logging
      - -c
      - log_destination=stderr
      - -c
      - logging_collector=off
      - -c
      - log_min_duration_statement=1000
      - -c
      - log_checkpoints=on
      - -c
      - log_connections=on
      - -c
      - log_disconnections=on
      - -c
      - log_lock_waits=on
      # Statistics
      - -c
      - track_activities=on
      - -c
      - track_counts=on
      - -c
      - track_io_timing=on
      # Autovacuum
      - -c
      - autovacuum=on
      - -c
      - autovacuum_max_workers=3
      - -c
      - autovacuum_naptime=1min
    deploy:
      resources:
        limits:
          memory: 1024M
          cpus: "2.0"
        reservations:
          memory: 512M
          cpus: "0.5"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "pg_isready -U soma -d somastack && psql -U soma -d somastack -c 'SELECT 1'"]
    networks:
      somastack_net:
        aliases:
          - postgres
          - db.somastack.local
    logging: *default-logging
    shm_size: 256mb

  # --------------------------------------------------------------------------
  # Redis - Cache & Distributed Locks
  # --------------------------------------------------------------------------
  
  redis:
    image: redis:7-alpine
    container_name: somastack_redis
    hostname: redis
    <<: [*restart-policy, *security-opts, *common-labels]
    command:
      - redis-server
      - /etc/redis/redis.conf
      # Memory Management
      - --maxmemory
      - "400mb"
      - --maxmemory-policy
      - allkeys-lru
      - --maxmemory-samples
      - "10"
      # Persistence - AOF for durability
      - --appendonly
      - "yes"
      - --appendfsync
      - everysec
      - --auto-aof-rewrite-percentage
      - "100"
      - --auto-aof-rewrite-min-size
      - "64mb"
      # RDB Snapshots
      - --save
      - "900 1"
      - --save
      - "300 10"
      - --save
      - "60 10000"
      # Network
      - --tcp-backlog
      - "511"
      - --timeout
      - "0"
      - --tcp-keepalive
      - "300"
      # Performance
      - --activerehashing
      - "yes"
      - --hz
      - "10"
      # Logging
      - --loglevel
      - notice
      # Security
      - --protected-mode
      - "no"
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./config/redis/redis.conf:/etc/redis/redis.conf:ro
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.25"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "redis-cli", "ping"]
    networks:
      somastack_net:
        aliases:
          - redis
          - cache.somastack.local
    logging: *default-logging
    sysctls:
      net.core.somaxconn: "1024"

  # --------------------------------------------------------------------------
  # Milvus - Vector Database
  # --------------------------------------------------------------------------
  
  milvus:
    image: milvusdb/milvus:v2.3.3
    container_name: somastack_milvus
    hostname: milvus
    <<: [*restart-policy, *common-labels]
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      
      # Common Settings
      COMMON_STORAGETYPE: minio
      
      # Query Node Settings
      QUERYNODE_GRACEFULTIME: 5000
      QUERYNODE_LOADMEMORYLIMIT: 1.5
      
      # Data Node Settings
      DATANODE_SEGMENT_INSERTBUFFERSIZE: 16777216
      
      # Index Settings
      INDEXNODE_SCHEDULER_BUILDPARALLEL: 1
    ports:
      - "19530:19530"  # gRPC
      - "9091:9091"    # Metrics
    volumes:
      - milvus_data:/var/lib/milvus
      - ./config/milvus/milvus.yaml:/milvus/configs/milvus.yaml:ro
    deploy:
      resources:
        limits:
          memory: 2048M
          cpus: "2.0"
        reservations:
          memory: 1024M
          cpus: "0.5"
    depends_on:
      etcd:
        condition: service_healthy
      minio:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      start_period: 180s
    networks:
      somastack_net:
        aliases:
          - milvus
          - vectors.somastack.local
    logging: *default-logging

  # --------------------------------------------------------------------------
  # etcd - Distributed Key-Value Store (Milvus metadata)
  # --------------------------------------------------------------------------
  
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    container_name: somastack_etcd
    hostname: etcd
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Cluster Settings
      ETCD_NAME: etcd0
      ETCD_DATA_DIR: /etcd-data
      
      # Client URLs
      ETCD_LISTEN_CLIENT_URLS: http://0.0.0.0:2379
      ETCD_ADVERTISE_CLIENT_URLS: http://etcd:2379
      
      # Peer URLs (single node)
      ETCD_LISTEN_PEER_URLS: http://0.0.0.0:2380
      ETCD_INITIAL_ADVERTISE_PEER_URLS: http://etcd:2380
      ETCD_INITIAL_CLUSTER: etcd0=http://etcd:2380
      ETCD_INITIAL_CLUSTER_STATE: new
      ETCD_INITIAL_CLUSTER_TOKEN: somastack-etcd-cluster
      
      # Compaction
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: "1000"
      
      # Quota
      ETCD_QUOTA_BACKEND_BYTES: "4294967296"  # 4GB
      
      # Logging
      ETCD_LOG_LEVEL: info
      ETCD_LOG_OUTPUTS: stderr
      
      # Metrics
      ETCD_LISTEN_METRICS_URLS: http://0.0.0.0:2381
    ports:
      - "2379:2379"   # Client
      - "2380:2380"   # Peer
      - "2381:2381"   # Metrics
    volumes:
      - etcd_data:/etcd-data
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
        reservations:
          memory: 128M
          cpus: "0.1"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "etcdctl", "endpoint", "health", "--endpoints=http://localhost:2379"]
    networks:
      somastack_net:
        aliases:
          - etcd
          - etcd.somastack.local
    logging: *default-logging

  # --------------------------------------------------------------------------
  # MinIO - Object Storage (S3-compatible)
  # --------------------------------------------------------------------------
  
  minio:
    image: minio/minio:RELEASE.2024-01-01T16-36-33Z
    container_name: somastack_minio
    hostname: minio
    <<: [*restart-policy, *security-opts, *common-labels]
    command: server /data --console-address ":9001"
    environment:
      # Root Credentials
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
      
      # Region
      MINIO_REGION: us-east-1
      
      # Browser
      MINIO_BROWSER: "on"
      MINIO_BROWSER_REDIRECT_URL: http://localhost:9001
      
      # Prometheus Metrics
      MINIO_PROMETHEUS_AUTH_TYPE: public
      MINIO_PROMETHEUS_URL: http://prometheus:9090
      
      # Logging
      MINIO_LOGGER_WEBHOOK_ENABLE_PRIMARY: "off"
      
      # Scanner
      MINIO_SCANNER_SPEED: default
    ports:
      - "9000:9000"   # API
      - "9001:9001"   # Console
    volumes:
      - minio_data:/data
      - ./config/minio/policies:/policies:ro
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.25"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    networks:
      somastack_net:
        aliases:
          - minio
          - s3.somastack.local
    logging: *default-logging

  # MinIO Client - For bucket initialization
  minio-init:
    image: minio/mc:latest
    container_name: somastack_minio_init
    <<: [*common-labels]
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set somastack http://minio:9000 minioadmin minioadmin;
      mc mb --ignore-existing somastack/flink-checkpoints;
      mc mb --ignore-existing somastack/flink-savepoints;
      mc mb --ignore-existing somastack/milvus;
      mc mb --ignore-existing somastack/backups;
      mc mb --ignore-existing somastack/logs;
      mc anonymous set download somastack/logs;
      echo 'Buckets created successfully';
      exit 0;
      "
    networks:
      - somastack_net
    profiles:
      - init

  # --------------------------------------------------------------------------
  # Schema Registry - Avro/Protobuf Schema Management
  # --------------------------------------------------------------------------
  
  schema-registry:
    image: apicurio/apicurio-registry-mem:2.5.8.Final
    container_name: somastack_schema_registry
    hostname: schema-registry
    <<: [*restart-policy, *common-labels]
    environment:
      # Registry Settings
      REGISTRY_AUTH_ANONYMOUS_READ_ACCESS_ENABLED: "true"
      REGISTRY_UI_FEATURES_READONLY: "false"
      
      # Logging
      LOG_LEVEL: INFO
      QUARKUS_LOG_CONSOLE_ENABLE: "true"
      
      # HTTP
      QUARKUS_HTTP_PORT: 8080
      QUARKUS_HTTP_CORS: "true"
      QUARKUS_HTTP_CORS_ORIGINS: "*"
    ports:
      - "8082:8080"
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
        reservations:
          memory: 128M
          cpus: "0.1"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health/ready || exit 1"]
    networks:
      somastack_net:
        aliases:
          - schema-registry
          - schemas.somastack.local
    logging: *default-logging

  # ============================================================================
  # 📊 OBSERVABILITY LAYER
  # ============================================================================
  
  # --------------------------------------------------------------------------
  # Jaeger - Distributed Tracing
  # --------------------------------------------------------------------------
  
  jaeger:
    image: jaegertracing/all-in-one:1.53
    container_name: somastack_jaeger
    hostname: jaeger
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Collector Settings
      COLLECTOR_OTLP_ENABLED: "true"
      COLLECTOR_ZIPKIN_HOST_PORT: ":9411"
      
      # Storage - Memory (Elasticsearch/Cassandra in production)
      SPAN_STORAGE_TYPE: memory
      MEMORY_MAX_TRACES: 10000
      
      # Sampling
      SAMPLING_STRATEGIES_FILE: /etc/jaeger/sampling.json
      
      # Query Service
      QUERY_BASE_PATH: /jaeger
      QUERY_UI_CONFIG: /etc/jaeger/ui-config.json
      
      # Metrics
      METRICS_BACKEND: prometheus
      PROMETHEUS_SERVER_URL: http://prometheus:9090
      
      # Logging
      LOG_LEVEL: info
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
      - "14268:14268"  # Jaeger HTTP Thrift
      - "14250:14250"  # Jaeger gRPC
      - "9411:9411"    # Zipkin compatible
      - "6831:6831/udp"  # Jaeger Thrift compact
    volumes:
      - ./config/jaeger/sampling.json:/etc/jaeger/sampling.json:ro
      - ./config/jaeger/ui-config.json:/etc/jaeger/ui-config.json:ro
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
        reservations:
          memory: 128M
          cpus: "0.1"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "wget -q --spider http://localhost:14269/health || exit 1"]
    networks:
      somastack_net:
        aliases:
          - jaeger
          - tracing.somastack.local
    logging: *default-logging

  # --------------------------------------------------------------------------
  # Prometheus - Metrics Collection
  # --------------------------------------------------------------------------
  
  prometheus:
    image: prom/prometheus:v2.49.0
    container_name: somastack_prometheus
    hostname: prometheus
    <<: [*restart-policy, *security-opts, *common-labels]
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=7d
      - --storage.tsdb.retention.size=5GB
      - --web.console.libraries=/usr/share/prometheus/console_libraries
      - --web.console.templates=/usr/share/prometheus/consoles
      - --web.enable-lifecycle
      - --web.enable-admin-api
      - --web.external-url=http://localhost:9090
      - --log.level=info
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/prometheus/alerts:/etc/prometheus/alerts:ro
      - ./config/prometheus/recording_rules.yml:/etc/prometheus/recording_rules.yml:ro
      - prometheus_data:/prometheus
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.25"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "wget -q --spider http://localhost:9090/-/healthy || exit 1"]
    networks:
      somastack_net:
        aliases:
          - prometheus
          - metrics.somastack.local
    logging: *default-logging

  # --------------------------------------------------------------------------
  # Grafana - Dashboards & Visualization
  # --------------------------------------------------------------------------
  
  grafana:
    image: grafana/grafana:10.3.1
    container_name: somastack_grafana
    hostname: grafana
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Security
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_USERS_ALLOW_ORG_CREATE: "false"
      
      # Server
      GF_SERVER_ROOT_URL: http://localhost:3000
      GF_SERVER_SERVE_FROM_SUB_PATH: "false"
      
      # Database (SQLite for local)
      GF_DATABASE_TYPE: sqlite3
      GF_DATABASE_PATH: /var/lib/grafana/grafana.db
      
      # Logging
      GF_LOG_MODE: console
      GF_LOG_LEVEL: info
      
      # Plugins
      GF_INSTALL_PLUGINS: grafana-clock-panel,grafana-piechart-panel,grafana-polystat-panel
      
      # Alerting
      GF_ALERTING_ENABLED: "true"
      GF_UNIFIED_ALERTING_ENABLED: "true"
      
      # Feature Toggles
      GF_FEATURE_TOGGLES_ENABLE: tempoSearch,tempoBackendSearch,tempoServiceGraph
      
      # Anonymous Access (for local dev)
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
    ports:
      - "3000:3000"
    volumes:
      - ./config/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./config/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
        reservations:
          memory: 128M
          cpus: "0.1"
    depends_on:
      prometheus:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "wget -q --spider http://localhost:3000/api/health || exit 1"]
    networks:
      somastack_net:
        aliases:
          - grafana
          - dashboards.somastack.local
    logging: *default-logging

  # --------------------------------------------------------------------------
  # Loki - Log Aggregation
  # --------------------------------------------------------------------------
  
  loki:
    image: grafana/loki:2.9.4
    container_name: somastack_loki
    hostname: loki
    <<: [*restart-policy, *security-opts, *common-labels]
    command: -config.file=/etc/loki/loki-config.yaml
    ports:
      - "3100:3100"   # HTTP API
      - "9096:9096"   # gRPC
    volumes:
      - ./config/loki/loki-config.yaml:/etc/loki/loki-config.yaml:ro
      - loki_data:/loki
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
        reservations:
          memory: 128M
          cpus: "0.1"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "wget -q --spider http://localhost:3100/ready || exit 1"]
    networks:
      somastack_net:
        aliases:
          - loki
          - logs.somastack.local
    logging: *default-logging

  # --------------------------------------------------------------------------
  # Promtail - Log Shipper
  # --------------------------------------------------------------------------
  
  promtail:
    image: grafana/promtail:2.9.4
    container_name: somastack_promtail
    hostname: promtail
    <<: [*restart-policy, *common-labels]
    command: -config.file=/etc/promtail/promtail-config.yaml
    volumes:
      - ./config/promtail/promtail-config.yaml:/etc/promtail/promtail-config.yaml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.25"
        reservations:
          memory: 64M
          cpus: "0.1"
    depends_on:
      loki:
        condition: service_healthy
    networks:
      - somastack_net
    logging: *default-logging

  # --------------------------------------------------------------------------
  # OPA - Open Policy Agent
  # --------------------------------------------------------------------------
  
  opa:
    image: openpolicyagent/opa:0.61.0
    container_name: somastack_opa
    hostname: opa
    <<: [*restart-policy, *security-opts, *common-labels]
    command:
      - run
      - --server
      - --addr=0.0.0.0:8181
      - --diagnostic-addr=0.0.0.0:8282
      - --log-level=info
      - --log-format=json
      - --set=decision_logs.console=true
      - --set=status.console=true
      - /policies
    ports:
      - "8181:8181"   # API
      - "8282:8282"   # Diagnostics
    volumes:
      - ./config/opa/policies:/policies:ro
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.25"
        reservations:
          memory: 64M
          cpus: "0.1"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "wget -q --spider http://localhost:8181/health || exit 1"]
    networks:
      somastack_net:
        aliases:
          - opa
          - policy.somastack.local
    logging: *default-logging

  # ============================================================================
  # 🧠 SOMA SERVICES (Profiles for selective startup)
  # ============================================================================
  
  # --------------------------------------------------------------------------
  # SomaBrain - Cognitive Processing Service
  # --------------------------------------------------------------------------
  
  somabrain:
    image: somabrain:latest
    build:
      context: ../somabrain
      dockerfile: Dockerfile
    container_name: somastack_somabrain
    hostname: somabrain
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Service Identity
      SERVICE_NAME: somabrain
      SERVICE_VERSION: "1.0.0"
      ENVIRONMENT: somastack
      
      # Database
      POSTGRES_URL: postgresql://soma:soma@postgres:5432/somastack
      DATABASE_POOL_SIZE: 10
      DATABASE_MAX_OVERFLOW: 20
      
      # Redis
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_DB: 0
      
      # Milvus
      SOMA_MILVUS_HOST: milvus
      SOMA_MILVUS_PORT: 19530
      
      # Kafka
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      KAFKA_CONSUMER_GROUP: somabrain-consumer
      
      # Tracing
      OTEL_EXPORTER_OTLP_ENDPOINT: http://jaeger:4318
      OTEL_SERVICE_NAME: somabrain
      OTEL_TRACES_SAMPLER: parentbased_traceidratio
      OTEL_TRACES_SAMPLER_ARG: "1.0"
      
      # Metrics
      PROMETHEUS_MULTIPROC_DIR: /tmp/prometheus
      
      # Logging
      LOG_LEVEL: INFO
      LOG_FORMAT: json
      
      # API
      SOMA_API_TOKEN: devtoken
      API_HOST: 0.0.0.0
      API_PORT: 9696
    ports:
      - "9696:9696"
    volumes:
      - somabrain_data:/app/data
      - ./config/somabrain:/app/config:ro
    deploy:
      resources:
        limits:
          memory: 2048M
          cpus: "2.0"
        reservations:
          memory: 1024M
          cpus: "0.5"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka:
        condition: service_healthy
      milvus:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -sf http://localhost:9696/health || exit 1"]
      start_period: 120s
    networks:
      somastack_net:
        aliases:
          - somabrain
          - brain.somastack.local
    logging: *default-logging
    profiles:
      - soma
      - full

  # --------------------------------------------------------------------------
  # SomaAgent01 - Agent Orchestration Service
  # --------------------------------------------------------------------------
  
  somaagent:
    image: somaagent01:latest
    build:
      context: ../somaAgent01
      dockerfile: Dockerfile
    container_name: somastack_somaagent
    hostname: somaagent
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Service Identity
      SERVICE_NAME: somaagent01
      SERVICE_VERSION: "1.0.0"
      ENVIRONMENT: somastack
      
      # Database
      SA01_DB_DSN: postgresql://soma:soma@postgres:5432/somastack
      
      # Redis
      SA01_REDIS_URL: redis://redis:6379/1
      
      # Kafka
      SA01_KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      
      # Temporal
      TEMPORAL_ADDRESS: temporal:7233
      TEMPORAL_NAMESPACE: somastack
      
      # SomaBrain Integration
      SOMA_BASE_URL: http://somabrain:9696
      SOMA_API_TOKEN: devtoken
      
      # SomaFractalMemory Integration
      SOMA_MEMORY_URL: http://somamemory:9595
      
      # Tracing
      OTEL_EXPORTER_OTLP_ENDPOINT: http://jaeger:4318
      OTEL_SERVICE_NAME: somaagent01
      
      # Gateway
      GATEWAY_PORT: 21016
      GATEWAY_HOST: 0.0.0.0
      
      # Auth
      SA01_AUTH_INTERNAL_TOKEN: internal-dev-token
      SA01_POLICY_URL: http://opa:8181
      
      # Logging
      LOG_LEVEL: INFO
    ports:
      - "21016:21016"
    volumes:
      - somaagent_data:/app/data
      - ./config/somaagent:/app/config:ro
    deploy:
      resources:
        limits:
          memory: 2048M
          cpus: "2.0"
        reservations:
          memory: 1024M
          cpus: "0.5"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka:
        condition: service_healthy
      temporal:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -sf http://localhost:21016/v1/health || exit 1"]
      start_period: 120s
    networks:
      somastack_net:
        aliases:
          - somaagent
          - agent.somastack.local
    logging: *default-logging
    profiles:
      - soma
      - full

  # --------------------------------------------------------------------------
  # SomaFractalMemory - Memory Service
  # --------------------------------------------------------------------------
  
  somamemory:
    image: somafractalmemory:latest
    build:
      context: ../somafractalmemory
      dockerfile: Dockerfile
    container_name: somastack_somamemory
    hostname: somamemory
    <<: [*restart-policy, *security-opts, *common-labels]
    environment:
      # Service Identity
      SERVICE_NAME: somafractalmemory
      SERVICE_VERSION: "1.0.0"
      ENVIRONMENT: somastack
      
      # Database
      POSTGRES_URL: postgresql://soma:soma@postgres:5432/somastack
      
      # Redis
      REDIS_HOST: redis
      REDIS_PORT: 6379
      
      # Milvus
      SOMA_MILVUS_HOST: milvus
      SOMA_MILVUS_PORT: 19530
      
      # Kafka
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      
      # Tracing
      OTEL_EXPORTER_OTLP_ENDPOINT: http://jaeger:4318
      OTEL_SERVICE_NAME: somafractalmemory
      
      # API
      SOMA_API_TOKEN: devtoken
      API_HOST: 0.0.0.0
      API_PORT: 9595
      
      # Logging
      LOG_LEVEL: INFO
    ports:
      - "9595:9595"
    volumes:
      - somamemory_data:/app/data
      - ./config/somamemory:/app/config:ro
    deploy:
      resources:
        limits:
          memory: 1024M
          cpus: "1.0"
        reservations:
          memory: 512M
          cpus: "0.25"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      milvus:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -sf http://localhost:9595/healthz || exit 1"]
      start_period: 90s
    networks:
      somastack_net:
        aliases:
          - somamemory
          - memory.somastack.local
    logging: *default-logging
    profiles:
      - soma
      - full

  # --------------------------------------------------------------------------
  # AgentVoiceBox - Voice Interface Service
  # --------------------------------------------------------------------------
  
  somavoice:
    image: agentvoicebox:latest
    build:
      context: ../agentVoiceBox
      dockerfile: Dockerfile
    container_name: somastack_somavoice
    hostname: somavoice
    <<: [*restart-policy, *common-labels]
    environment:
      # Service Identity
      SERVICE_NAME: agentvoicebox
      SERVICE_VERSION: "1.0.0"
      ENVIRONMENT: somastack
      
      # SomaAgent Integration
      SOMA_AGENT_URL: http://somaagent:21016
      
      # Tracing
      OTEL_EXPORTER_OTLP_ENDPOINT: http://jaeger:4318
      OTEL_SERVICE_NAME: agentvoicebox
      
      # API
      API_HOST: 0.0.0.0
      API_PORT: 25000
      
      # Logging
      LOG_LEVEL: INFO
    ports:
      - "25000:25000"
    volumes:
      - somavoice_data:/app/data
      - ./config/somavoice:/app/config:ro
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
        reservations:
          memory: 256M
          cpus: "0.25"
    depends_on:
      somaagent:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -sf http://localhost:25000/health || exit 1"]
      start_period: 60s
    networks:
      somastack_net:
        aliases:
          - somavoice
          - voice.somastack.local
    logging: *default-logging
    profiles:
      - voice
      - full

# ============================================================================
# 💾 VOLUMES - Persistent Storage
# ============================================================================

volumes:
  # Event Streaming
  kafka_data:
    name: somastack_kafka_data
  kafka_logs:
    name: somastack_kafka_logs
  flink_checkpoints:
    name: somastack_flink_checkpoints
  flink_savepoints:
    name: somastack_flink_savepoints
  flink_uploads:
    name: somastack_flink_uploads
  flink_tm_data:
    name: somastack_flink_tm_data
  
  # Workflow
  temporal_data:
    name: somastack_temporal_data
  kong_prefix:
    name: somastack_kong_prefix
  
  # Data Stores
  postgres_data:
    name: somastack_postgres_data
  postgres_backups:
    name: somastack_postgres_backups
  redis_data:
    name: somastack_redis_data
  milvus_data:
    name: somastack_milvus_data
  etcd_data:
    name: somastack_etcd_data
  minio_data:
    name: somastack_minio_data
  
  # Observability
  prometheus_data:
    name: somastack_prometheus_data
  grafana_data:
    name: somastack_grafana_data
  loki_data:
    name: somastack_loki_data
  
  # Soma Services
  somabrain_data:
    name: somastack_somabrain_data
  somaagent_data:
    name: somastack_somaagent_data
  somamemory_data:
    name: somastack_somamemory_data
  somavoice_data:
    name: somastack_somavoice_data

# ============================================================================
# 🌐 NETWORKS
# ============================================================================

networks:
  somastack_net:
    name: somastack_net
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.28.0.0/16
          gateway: 172.28.0.1
    driver_opts:
      com.docker.network.bridge.enable_icc: "true"
      com.docker.network.bridge.enable_ip_masquerade: "true"
      com.docker.network.bridge.host_binding_ipv4: "0.0.0.0"
      com.docker.network.driver.mtu: "1500"
```ioning:ro
      - grafana_data:/var/lib/grafana
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M
    networks:
      - somastack_net

  loki:
    image: grafana/loki:2.9.4
    container_name: somastack_loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    volumes:
      - ./config/loki/loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M
    networks:
      - somastack_net

  opa:
    image: openpolicyagent/opa:0.61.0
    container_name: somastack_opa
    command:
      - run
      - --server
      - --addr=0.0.0.0:8181
      - /policies
    ports:
      - "8181:8181"
    volumes:
      - ./config/opa/policies:/policies:ro
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
    networks:
      - somastack_net

volumes:
  kafka_data:
  postgres_data:
  redis_data:
  milvus_data:
  etcd_data:
  minio_data:
  prometheus_data:
  grafana_data:
  loki_data:

networks:
  somastack_net:
    name: somastack_net
    driver: bridge
```

### Configuration Files Structure

Now let me define all the configuration files that need to be created:

```
somastack/
├── config/
│   ├── kafka/
│   │   └── server.properties           # Kafka broker config
│   ├── flink/
│   │   ├── flink-conf.yaml             # Flink configuration
│   │   └── log4j-console.properties    # Flink logging
│   ├── temporal/
│   │   ├── dynamicconfig.yaml          # Temporal dynamic config
│   │   └── development.yaml            # Temporal server config
│   ├── kong/
│   │   ├── kong.yaml                   # Kong declarative config
│   │   └── ssl/
│   │       ├── kong.crt                # Self-signed cert
│   │       └── kong.key                # Private key
│   ├── postgres/
│   │   ├── postgresql.conf             # PostgreSQL config
│   │   ├── pg_hba.conf                 # PostgreSQL auth
│   │   └── init/
│   │       ├── 01-databases.sql        # Create databases
│   │       ├── 02-extensions.sql       # Enable extensions
│   │       ├── 03-events.sql           # Event store schema
│   │       ├── 04-sagas.sql            # Saga state schema
│   │       └── 05-users.sql            # Service users
│   ├── redis/
│   │   └── redis.conf                  # Redis configuration
│   ├── milvus/
│   │   └── milvus.yaml                 # Milvus configuration
│   ├── minio/
│   │   └── policies/
│   │       └── readwrite.json          # Bucket policies
│   ├── prometheus/
│   │   ├── prometheus.yml              # Prometheus config
│   │   ├── recording_rules.yml         # Recording rules
│   │   └── alerts/
│   │       ├── somastack.yml           # SomaStack alerts
│   │       └── infrastructure.yml      # Infra alerts
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   │   └── datasources.yaml    # Auto-provision datasources
│   │   │   └── dashboards/
│   │   │       └── dashboards.yaml     # Dashboard provisioning
│   │   └── dashboards/
│   │       ├── somastack-overview.json # Main dashboard
│   │       ├── kafka-metrics.json      # Kafka dashboard
│   │       ├── flink-metrics.json      # Flink dashboard
│   │       └── services-metrics.json   # Services dashboard
│   ├── loki/
│   │   └── loki-config.yaml            # Loki configuration
│   ├── promtail/
│   │   └── promtail-config.yaml        # Promtail configuration
│   ├── jaeger/
│   │   ├── sampling.json               # Sampling strategies
│   │   └── ui-config.json              # UI configuration
│   ├── opa/
│   │   └── policies/
│   │       ├── authz.rego              # Authorization policy
│   │       ├── rbac.rego               # RBAC policy
│   │       └── data.json               # Policy data
│   ├── somabrain/
│   │   └── config.yaml                 # SomaBrain config
│   ├── somaagent/
│   │   └── config.yaml                 # SomaAgent config
│   ├── somamemory/
│   │   └── config.yaml                 # SomaMemory config
│   └── somavoice/
│       └── config.yaml                 # SomaVoice config
```

### PostgreSQL Initialization Scripts

```sql
-- config/postgres/init/01-databases.sql
-- Create separate databases for each service (optional, can use schemas)

-- Main SomaStack database is created by POSTGRES_DB env var
-- Create additional databases if needed
-- CREATE DATABASE somabrain;
-- CREATE DATABASE somaagent;
-- CREATE DATABASE somamemory;

-- Create schemas for logical separation
CREATE SCHEMA IF NOT EXISTS events;
CREATE SCHEMA IF NOT EXISTS sagas;
CREATE SCHEMA IF NOT EXISTS somabrain;
CREATE SCHEMA IF NOT EXISTS somaagent;
CREATE SCHEMA IF NOT EXISTS somamemory;
CREATE SCHEMA IF NOT EXISTS temporal;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA events TO soma;
GRANT ALL PRIVILEGES ON SCHEMA sagas TO soma;
GRANT ALL PRIVILEGES ON SCHEMA somabrain TO soma;
GRANT ALL PRIVILEGES ON SCHEMA somaagent TO soma;
GRANT ALL PRIVILEGES ON SCHEMA somamemory TO soma;
GRANT ALL PRIVILEGES ON SCHEMA temporal TO soma;
```

```sql
-- config/postgres/init/02-extensions.sql
-- Enable required PostgreSQL extensions

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Full-text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- JSON operations
CREATE EXTENSION IF NOT EXISTS "jsonb_plperl" CASCADE;

-- Statistics
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Logical replication for CDC
-- Already enabled via wal_level=logical in postgres command
```

```sql
-- config/postgres/init/03-events.sql
-- Event Store Schema

SET search_path TO events, public;

-- Events table (append-only, partitioned by month)
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL,
    event_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(64) NOT NULL,
    service_id VARCHAR(50) NOT NULL,
    tenant_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    schema_version VARCHAR(10) DEFAULT '1.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (id, timestamp),
    CONSTRAINT events_event_id_unique UNIQUE (event_id)
) PARTITION BY RANGE (timestamp);

-- Create partitions for current and next 3 months
CREATE TABLE IF NOT EXISTS events_2025_01 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE IF NOT EXISTS events_2025_02 PARTITION OF events
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE IF NOT EXISTS events_2025_03 PARTITION OF events
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE IF NOT EXISTS events_default PARTITION OF events DEFAULT;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_trace_id ON events (trace_id);
CREATE INDEX IF NOT EXISTS idx_events_correlation_id ON events (correlation_id);
CREATE INDEX IF NOT EXISTS idx_events_tenant_service ON events (tenant_id, service_id);
CREATE INDEX IF NOT EXISTS idx_events_type_timestamp ON events (event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_payload_gin ON events USING GIN (payload jsonb_path_ops);

-- Idempotency keys table
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys (expires_at);

-- Outbox table for transactional messaging
CREATE TABLE IF NOT EXISTS outbox (
    id BIGSERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    partition_key VARCHAR(255),
    payload JSONB NOT NULL,
    headers JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending',
    retries INT DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox (status, created_at);

-- Function to auto-create monthly partitions
CREATE OR REPLACE FUNCTION create_events_partition()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- Create partition for next month
    partition_date := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    partition_name := 'events_' || TO_CHAR(partition_date, 'YYYY_MM');
    start_date := partition_date;
    end_date := partition_date + INTERVAL '1 month';
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS events.%I PARTITION OF events.events FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;
```

```sql
-- config/postgres/init/04-sagas.sql
-- Saga State Schema

SET search_path TO sagas, public;

-- Saga definitions table
CREATE TABLE IF NOT EXISTS saga_definitions (
    saga_type VARCHAR(100) PRIMARY KEY,
    steps JSONB NOT NULL,
    timeout_seconds INT DEFAULT 300,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Saga instances table
CREATE TABLE IF NOT EXISTS saga_instances (
    saga_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    saga_type VARCHAR(100) NOT NULL REFERENCES saga_definitions(saga_type),
    trace_id VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    current_step INT DEFAULT 0,
    completed_steps JSONB DEFAULT '[]',
    step_results JSONB DEFAULT '{}',
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'compensating', 'failed', 'rolled_back'))
);

CREATE INDEX IF NOT EXISTS idx_sagas_trace_id ON saga_instances (trace_id);
CREATE INDEX IF NOT EXISTS idx_sagas_correlation_id ON saga_instances (correlation_id);
CREATE INDEX IF NOT EXISTS idx_sagas_tenant_status ON saga_instances (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_sagas_status_updated ON saga_instances (status, updated_at);

-- Saga step log (audit trail)
CREATE TABLE IF NOT EXISTS saga_step_log (
    id BIGSERIAL PRIMARY KEY,
    saga_id UUID NOT NULL REFERENCES saga_instances(saga_id),
    step_index INT NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL, -- 'execute' or 'compensate'
    status VARCHAR(20) NOT NULL,
    input JSONB,
    output JSONB,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INT
);

CREATE INDEX IF NOT EXISTS idx_saga_step_log_saga ON saga_step_log (saga_id, step_index);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_saga_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER saga_instances_updated
    BEFORE UPDATE ON saga_instances
    FOR EACH ROW
    EXECUTE FUNCTION update_saga_timestamp();
```

```sql
-- config/postgres/init/05-users.sql
-- Service Users and Permissions

-- Create read-only user for reporting
CREATE USER soma_readonly WITH PASSWORD 'soma_readonly';
GRANT CONNECT ON DATABASE somastack TO soma_readonly;
GRANT USAGE ON SCHEMA events, sagas, somabrain, somaagent, somamemory TO soma_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA events, sagas, somabrain, somaagent, somamemory TO soma_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA events, sagas, somabrain, somaagent, somamemory 
    GRANT SELECT ON TABLES TO soma_readonly;

-- Create replication user for CDC (Debezium)
CREATE USER soma_replication WITH REPLICATION PASSWORD 'soma_replication';
GRANT CONNECT ON DATABASE somastack TO soma_replication;
GRANT USAGE ON SCHEMA events TO soma_replication;
GRANT SELECT ON ALL TABLES IN SCHEMA events TO soma_replication;

-- Create publication for CDC
CREATE PUBLICATION somastack_cdc FOR TABLE events.events, events.outbox;
```

### Prometheus Configuration

```yaml
# config/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: somastack-local
    environment: development

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files:
  - /etc/prometheus/recording_rules.yml
  - /etc/prometheus/alerts/*.yml

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Kafka metrics
  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka:9999']
    metrics_path: /metrics

  # Flink metrics
  - job_name: 'flink-jobmanager'
    static_configs:
      - targets: ['flink-jobmanager:9249']

  - job_name: 'flink-taskmanager'
    static_configs:
      - targets: ['flink-taskmanager:9249']

  # Temporal metrics
  - job_name: 'temporal'
    static_configs:
      - targets: ['temporal:9090']

  # PostgreSQL metrics (via postgres_exporter if added)
  # - job_name: 'postgres'
  #   static_configs:
  #     - targets: ['postgres-exporter:9187']

  # Redis metrics (via redis_exporter if added)
  # - job_name: 'redis'
  #   static_configs:
  #     - targets: ['redis-exporter:9121']

  # Milvus metrics
  - job_name: 'milvus'
    static_configs:
      - targets: ['milvus:9091']

  # Kong metrics
  - job_name: 'kong'
    static_configs:
      - targets: ['kong:8001']
    metrics_path: /metrics

  # Jaeger metrics
  - job_name: 'jaeger'
    static_configs:
      - targets: ['jaeger:14269']

  # Loki metrics
  - job_name: 'loki'
    static_configs:
      - targets: ['loki:3100']
    metrics_path: /metrics

  # OPA metrics
  - job_name: 'opa'
    static_configs:
      - targets: ['opa:8282']
    metrics_path: /metrics

  # SomaBrain metrics
  - job_name: 'somabrain'
    static_configs:
      - targets: ['somabrain:9696']
    metrics_path: /metrics

  # SomaAgent metrics
  - job_name: 'somaagent'
    static_configs:
      - targets: ['somaagent:21016']
    metrics_path: /metrics

  # SomaMemory metrics
  - job_name: 'somamemory'
    static_configs:
      - targets: ['somamemory:9595']
    metrics_path: /metrics

  # SomaVoice metrics
  - job_name: 'somavoice'
    static_configs:
      - targets: ['somavoice:25000']
    metrics_path: /metrics

  # Docker containers (via cAdvisor if added)
  # - job_name: 'cadvisor'
  #   static_configs:
  #     - targets: ['cadvisor:8080']
```

### Loki Configuration

```yaml
# config/loki/loki-config.yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: info

common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9093

limits_config:
  retention_period: 168h  # 7 days
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
  max_streams_per_user: 10000
  max_line_size: 256kb

compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
```

### Kong Gateway Configuration

```yaml
# config/kong/kong.yaml
_format_version: "3.0"
_transform: true

services:
  # SomaBrain API
  - name: somabrain-service
    url: http://somabrain:9696
    routes:
      - name: somabrain-route
        paths:
          - /api/brain
        strip_path: true
        plugins:
          - name: rate-limiting
            config:
              minute: 100
              policy: local
          - name: prometheus
            config:
              per_consumer: false

  # SomaAgent API
  - name: somaagent-service
    url: http://somaagent:21016
    routes:
      - name: somaagent-route
        paths:
          - /api/agent
        strip_path: true
        plugins:
          - name: rate-limiting
            config:
              minute: 100
              policy: local
          - name: prometheus

  # SomaMemory API
  - name: somamemory-service
    url: http://somamemory:9595
    routes:
      - name: somamemory-route
        paths:
          - /api/memory
        strip_path: true
        plugins:
          - name: rate-limiting
            config:
              minute: 200
              policy: local
          - name: prometheus

  # SomaVoice API
  - name: somavoice-service
    url: http://somavoice:25000
    routes:
      - name: somavoice-route
        paths:
          - /api/voice
        strip_path: true
        plugins:
          - name: rate-limiting
            config:
              minute: 50
              policy: local
          - name: prometheus

  # Temporal UI (internal)
  - name: temporal-ui-service
    url: http://temporal-ui:8080
    routes:
      - name: temporal-ui-route
        paths:
          - /temporal
        strip_path: true

  # Flink UI (internal)
  - name: flink-ui-service
    url: http://flink-jobmanager:8081
    routes:
      - name: flink-ui-route
        paths:
          - /flink
        strip_path: true

  # Grafana (internal)
  - name: grafana-service
    url: http://grafana:3000
    routes:
      - name: grafana-route
        paths:
          - /grafana
        strip_path: true

  # Jaeger UI (internal)
  - name: jaeger-service
    url: http://jaeger:16686
    routes:
      - name: jaeger-route
        paths:
          - /jaeger
        strip_path: true

plugins:
  # Global plugins
  - name: correlation-id
    config:
      header_name: X-Correlation-ID
      generator: uuid
      echo_downstream: true

  - name: request-transformer
    config:
      add:
        headers:
          - "X-SomaStack-Version:1.0.0"

  - name: prometheus
    config:
      status_code_metrics: true
      latency_metrics: true
      bandwidth_metrics: true
      upstream_health_metrics: true

consumers:
  - username: somastack-internal
    keyauth_credentials:
      - key: internal-dev-token

  - username: somastack-external
    keyauth_credentials:
      - key: external-dev-token
```

### OPA Authorization Policy

```rego
# config/opa/policies/authz.rego
package somastack.authz

import rego.v1

default allow := false

# Allow health checks without auth
allow if {
    input.path == ["health"]
}

allow if {
    input.path == ["healthz"]
}

allow if {
    input.path == ["metrics"]
}

# Allow internal service-to-service communication
allow if {
    input.headers["x-internal-token"] == "internal-dev-token"
}

# Allow requests with valid API token
allow if {
    input.headers["authorization"] == "Bearer devtoken"
}

# Allow requests with valid API key
allow if {
    input.headers["x-api-key"] == "external-dev-token"
}

# RBAC - Admin can do anything
allow if {
    user_is_admin
}

user_is_admin if {
    input.user.roles[_] == "admin"
}

# RBAC - Users can read their own tenant data
allow if {
    input.method == "GET"
    input.tenant_id == input.user.tenant_id
}

# RBAC - Users can write to their own tenant
allow if {
    input.method in ["POST", "PUT", "PATCH", "DELETE"]
    input.tenant_id == input.user.tenant_id
    not is_admin_endpoint
}

is_admin_endpoint if {
    input.path[0] == "admin"
}
```

### Grafana Datasources

```yaml
# config/grafana/provisioning/datasources/datasources.yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
      httpMethod: POST

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
    jsonData:
      maxLines: 1000

  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
    editable: false

  - name: PostgreSQL
    type: postgres
    url: postgres:5432
    database: somastack
    user: soma_readonly
    secureJsonData:
      password: soma_readonly
    jsonData:
      sslmode: disable
      maxOpenConns: 5
      maxIdleConns: 2
      connMaxLifetime: 14400
```

```
somastack/
├── Chart.yaml                    # Umbrella chart metadata
├── values.yaml                   # Default values
├── values-dev.yaml               # Development overrides
├── values-staging.yaml           # Staging overrides
├── values-prod.yaml              # Production overrides
├── templates/
│   ├── _helpers.tpl              # Template helpers
│   ├── namespace.yaml            # Namespace creation
│   ├── configmaps/               # Shared configurations
│   └── secrets/                  # External secrets references
└── charts/
    ├── kafka/                    # Strimzi Kafka
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    │       ├── kafka-cluster.yaml
    │       └── kafka-topics.yaml
    ├── flink/                    # Flink Kubernetes Operator
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    │       ├── flink-deployment.yaml
    │       └── flink-jobs.yaml
    ├── temporal/                 # Temporal
    │   └── (official chart)
    ├── kong/                     # Kong Ingress
    │   └── (official chart)
    ├── postgresql/               # CloudNativePG
    │   └── (official chart)
    ├── redis/                    # Redis Operator
    │   └── (official chart)
    ├── milvus/                   # Milvus
    │   └── (official chart)
    ├── observability/            # Prometheus stack
    │   ├── Chart.yaml
    │   └── templates/
    │       ├── prometheus.yaml
    │       ├── grafana.yaml
    │       ├── jaeger.yaml
    │       └── loki.yaml
    ├── security/                 # Security components
    │   ├── Chart.yaml
    │   └── templates/
    │       ├── opa.yaml
    │       ├── cert-manager.yaml
    │       └── external-secrets.yaml
    ├── somabrain/                # SomaBrain service
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    │       ├── deployment.yaml
    │       ├── service.yaml
    │       ├── hpa.yaml
    │       └── pdb.yaml
    ├── somaagent/                # SomaAgent01 service
    │   └── (similar structure)
    ├── somamemory/               # SomaFractalMemory service
    │   └── (similar structure)
    └── somavoice/                # AgentVoiceBox service
        └── (similar structure)
```

### Helm Values Example

```yaml
# values.yaml - Default configuration
global:
  deployMode: somastack  # standalone | somastack | production
  namespace: somastack
  imageRegistry: ""
  imagePullSecrets: []
  
  # Shared infrastructure endpoints (auto-configured in somastack mode)
  kafka:
    bootstrapServers: kafka:9092
  postgres:
    host: postgres
    port: 5432
    database: somastack
  redis:
    host: redis
    port: 6379
  milvus:
    host: milvus
    port: 19530
  jaeger:
    endpoint: http://jaeger:4318
  
  # Resource profiles
  resources:
    small:
      limits: { memory: 512Mi, cpu: 500m }
      requests: { memory: 256Mi, cpu: 100m }
    medium:
      limits: { memory: 1Gi, cpu: 1000m }
      requests: { memory: 512Mi, cpu: 250m }
    large:
      limits: { memory: 2Gi, cpu: 2000m }
      requests: { memory: 1Gi, cpu: 500m }

# Kafka configuration
kafka:
  enabled: true
  replicas: 1  # 3 in production
  resources: medium
  storage:
    size: 10Gi
  config:
    numPartitions: 3
    retentionHours: 168

# Flink configuration
flink:
  enabled: true
  jobManager:
    resources: small
  taskManager:
    replicas: 1  # 3 in production
    resources: medium
    taskSlots: 4
  checkpointing:
    interval: 30s
    storage: s3://flink-checkpoints

# Temporal configuration
temporal:
  enabled: true
  resources: medium
  persistence:
    driver: postgresql

# Kong configuration
kong:
  enabled: true
  resources: small
  proxy:
    type: LoadBalancer

# PostgreSQL configuration
postgresql:
  enabled: true
  instances: 1  # 3 in production
  resources: medium
  storage:
    size: 20Gi

# Redis configuration
redis:
  enabled: true
  replicas: 1  # 3 in production
  resources: small
  maxMemory: 400mb

# Milvus configuration
milvus:
  enabled: true
  standalone: true  # false for cluster mode in production
  resources: large

# Observability
observability:
  prometheus:
    enabled: true
    retention: 7d
    resources: small
  grafana:
    enabled: true
    resources: small
  jaeger:
    enabled: true
    resources: small
  loki:
    enabled: true
    resources: small

# Security
security:
  opa:
    enabled: true
    resources: small
  certManager:
    enabled: true
  externalSecrets:
    enabled: false  # true in production

# Soma Services
somabrain:
  enabled: true
  replicas: 1
  resources: large
  image:
    repository: somabrain
    tag: latest

somaagent:
  enabled: true
  replicas: 1
  resources: large
  image:
    repository: somaagent01
    tag: latest

somamemory:
  enabled: true
  replicas: 1
  resources: medium
  image:
    repository: somafractalmemory
    tag: latest

somavoice:
  enabled: false  # Optional component
  replicas: 1
  resources: small
  image:
    repository: agentvoicebox
    tag: latest
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do.*

### Property 1: Event Ordering Guarantee
*For any* two events E1 and E2 with the same partition key (tenant_id + aggregate_id), if E1.timestamp < E2.timestamp, then E1 SHALL be processed before E2 in all consumers.
**Validates: Requirements 5.5, 22.5**

### Property 2: Exactly-Once Event Delivery
*For any* event published to the Event Store, the event SHALL appear exactly once in both Kafka and PostgreSQL, regardless of retries or failures.
**Validates: Requirements 7.1, 7.2, 22.2**

### Property 3: Saga Compensation Completeness
*For any* saga that fails at step N, compensating actions SHALL be executed for all steps 1 to N-1 in reverse order (N-1, N-2, ..., 1).
**Validates: Requirements 5.1, 23.2**

### Property 4: Trace Context Propagation
*For any* request that crosses service boundaries, the trace_id SHALL remain constant across all services involved in the transaction.
**Validates: Requirements 4.4, 16.2**

### Property 5: Tenant Isolation
*For any* query to the Event Store with tenant_id=T, the result SHALL contain only events where event.tenant_id == T.
**Validates: Requirements 10.2, 22.4**

### Property 6: Idempotency Guarantee
*For any* event with idempotency_key=K processed multiple times, the side effects SHALL be applied exactly once.
**Validates: Requirements 7.3, 24.4**

### Property 7: Checkpoint Recovery
*For any* Flink job failure, the job SHALL resume from the last successful checkpoint with no data loss or duplication.
**Validates: Requirements 6.4, 6.3**

### Property 8: Resource Limits Enforcement
*For any* deployment in SomaStack mode, the total memory usage SHALL not exceed 15GB.
**Validates: Requirements 2.3 (implicit)**

### Property 9: Service Discovery Consistency
*For any* service in SomaStack mode, the infrastructure endpoints (Kafka, PostgreSQL, Redis) SHALL resolve to the shared instances.
**Validates: Requirements 2.4, 11.2**

### Property 10: Dead Letter Queue Capture
*For any* event that fails processing after max_retries, the event SHALL appear in the DLQ with original payload and error details preserved.
**Validates: Requirements 25.1, 25.2**

## Error Handling

### Error Categories

| Category | Examples | Handling Strategy |
|----------|----------|-------------------|
| **Transient** | Network timeout, Kafka unavailable | Retry with exponential backoff |
| **Recoverable** | Schema validation error, Invalid input | Return error, log, continue |
| **Fatal** | Database corruption, OOM | Alert, circuit break, manual intervention |
| **Business** | Insufficient funds, Duplicate request | Return business error, no retry |

### Circuit Breaker Configuration

```python
from pybreaker import CircuitBreaker

# Per-service circuit breakers
kafka_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    exclude=[ValueError, KeyError],  # Don't trip on business errors
)

postgres_breaker = CircuitBreaker(
    fail_max=3,
    reset_timeout=60,
)

# Usage
@kafka_breaker
async def publish_event(event: Event) -> bool:
    ...
```

### Retry Policy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type(TransientError),
)
async def publish_with_retry(event: Event) -> bool:
    ...
```

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies (Kafka, PostgreSQL)
- Focus on business logic correctness

### Integration Tests (Testcontainers)
```python
import pytest
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def kafka():
    with KafkaContainer() as kafka:
        yield kafka.get_bootstrap_server()

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url()

async def test_event_roundtrip(kafka, postgres):
    """Event published to Kafka appears in PostgreSQL."""
    store = EventStore(kafka=kafka, postgres=postgres)
    event = Event(...)
    await store.publish(event)
    
    # Verify in PostgreSQL
    events = await store.query(event_id=event.event_id)
    assert len(events) == 1
    assert events[0].payload == event.payload
```

### Property-Based Tests (Hypothesis)
```python
from hypothesis import given, strategies as st

@given(st.lists(st.builds(Event, ...)))
async def test_event_ordering_preserved(events):
    """Events maintain order within partition."""
    store = EventStore(...)
    for event in events:
        await store.publish(event)
    
    retrieved = await store.query(
        tenant_id=events[0].tenant_id,
        limit=len(events)
    )
    
    # Verify ordering
    timestamps = [e.timestamp for e in retrieved]
    assert timestamps == sorted(timestamps)
```

### Chaos Tests (Chaos Mesh)
```yaml
# chaos/kafka-failure.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: kafka-pod-failure
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - somastack
    labelSelectors:
      app: kafka
  duration: "30s"
  scheduler:
    cron: "@every 1h"
```

## CLI Tool Design

```bash
# somastack CLI
$ somastack --help
Usage: somastack [OPTIONS] COMMAND [ARGS]...

  SomaStack Platform CLI - Manage your AI agent ecosystem

Commands:
  up        Start SomaStack platform
  down      Stop SomaStack platform
  status    Show component health status
  logs      Tail logs from services
  events    Query and manage events
  saga      Inspect and manage sagas
  dlq       Manage dead letter queue
  config    Manage configuration

# Examples
$ somastack up --mode somastack
🚀 Starting SomaStack in somastack mode...
✅ Kafka ready (kafka:9092)
✅ PostgreSQL ready (postgres:5432)
✅ Redis ready (redis:6379)
✅ Flink ready (flink-jobmanager:8081)
✅ Temporal ready (temporal:7233)
✅ All infrastructure ready!

$ somastack status
┌─────────────────┬──────────┬─────────┬──────────┐
│ Component       │ Status   │ Memory  │ Uptime   │
├─────────────────┼──────────┼─────────┼──────────┤
│ kafka           │ ✅ healthy│ 1.2GB   │ 2h 15m   │
│ flink-jm        │ ✅ healthy│ 450MB   │ 2h 14m   │
│ flink-tm        │ ✅ healthy│ 890MB   │ 2h 14m   │
│ temporal        │ ✅ healthy│ 780MB   │ 2h 13m   │
│ postgres        │ ✅ healthy│ 650MB   │ 2h 15m   │
│ redis           │ ✅ healthy│ 380MB   │ 2h 15m   │
│ milvus          │ ✅ healthy│ 1.8GB   │ 2h 12m   │
│ somabrain       │ ✅ healthy│ 1.5GB   │ 1h 45m   │
│ somaagent       │ ✅ healthy│ 1.4GB   │ 1h 45m   │
└─────────────────┴──────────┴─────────┴──────────┘
Total Memory: 9.05GB / 15GB (60%)

$ somastack events list --trace-id abc123
┌──────────────────────────────────────────────────────────────┐
│ Trace: abc123                                                │
├──────────────────────────────────────────────────────────────┤
│ 10:15:32.123 │ soma.agent │ txn.started      │ Task created │
│ 10:15:32.456 │ soma.brain │ cognitive.eval   │ Planning...  │
│ 10:15:33.789 │ soma.memory│ memory.recalled  │ 5 memories   │
│ 10:15:34.012 │ soma.agent │ task.completed   │ Success      │
│ 10:15:34.234 │ soma.agent │ txn.committed    │ Done         │
└──────────────────────────────────────────────────────────────┘

$ somastack saga inspect saga-456
Saga ID: saga-456
Status: COMPLETED ✅
Steps:
  1. ✅ validate_input (10ms)
  2. ✅ store_memory (45ms)
  3. ✅ update_index (23ms)
  4. ✅ notify_agents (12ms)
Total Duration: 90ms
```



## Beautiful Logging Design

### Log Format

```python
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

class LogEmoji(str, Enum):
    """Emoji indicators for log types."""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    DEBUG = "🔍"
    COGNITIVE = "🧠"
    AGENT = "🤖"
    MEMORY = "💾"
    VOICE = "🎤"
    IN_PROGRESS = "🔄"
    TIMING = "⏱️"
    TRACE = "🔗"
    KAFKA = "📨"
    DATABASE = "🗄️"
    CACHE = "⚡"
    SAGA = "🎭"
    CHECKPOINT = "💾"

class SomaStackFormatter(logging.Formatter):
    """Beautiful, human-readable log formatter for SomaStack."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',
    }
    
    LEVEL_EMOJI = {
        'DEBUG': LogEmoji.DEBUG,
        'INFO': LogEmoji.INFO,
        'WARNING': LogEmoji.WARNING,
        'ERROR': LogEmoji.ERROR,
        'CRITICAL': LogEmoji.ERROR,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Extract trace context
        trace_id = getattr(record, 'trace_id', None)
        correlation_id = getattr(record, 'correlation_id', None)
        service_id = getattr(record, 'service_id', 'unknown')
        tenant_id = getattr(record, 'tenant_id', None)
        
        # Get emoji and color
        emoji = self.LEVEL_EMOJI.get(record.levelname, LogEmoji.INFO)
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Build log line
        parts = [
            f"{color}{emoji.value}{reset}",
            f"{timestamp}",
            f"[{service_id}]",
        ]
        
        if trace_id:
            parts.append(f"{LogEmoji.TRACE.value}{trace_id[:8]}")
        
        parts.append(f"{color}{record.levelname:8}{reset}")
        parts.append(record.getMessage())
        
        # Add extra data if present
        extra_data = getattr(record, 'data', None)
        if extra_data:
            if isinstance(extra_data, dict):
                # Pretty print JSON, truncate if too long
                json_str = json.dumps(extra_data, indent=2, default=str)
                if len(json_str) > 500:
                    json_str = json_str[:500] + "\n  ... [truncated]"
                parts.append(f"\n{json_str}")
        
        return " ".join(parts)

# Example output:
# ✅ 10:15:32.123 [somabrain] 🔗abc12345 INFO     Cognitive evaluation completed
# {
#   "duration_ms": 45,
#   "memories_recalled": 5,
#   "confidence": 0.92
# }
#
# 🔄 10:15:32.456 [somaagent] 🔗abc12345 INFO     Executing tool: web_search
# ❌ 10:15:33.789 [somaagent] 🔗abc12345 ERROR    Tool execution failed
# {
#   "tool": "web_search",
#   "error": "Connection timeout",
#   "retry_count": 2
# }
```

### Structured JSON Logging (for Loki)

```python
class SomaStackJSONFormatter(logging.Formatter):
    """JSON formatter for log aggregation systems."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": getattr(record, 'service_id', 'unknown'),
            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": getattr(record, 'trace_id', None),
            "correlation_id": getattr(record, 'correlation_id', None),
            "tenant_id": getattr(record, 'tenant_id', None),
            "span_id": getattr(record, 'span_id', None),
        }
        
        # Add extra data
        if hasattr(record, 'data'):
            log_entry["data"] = record.data
        
        # Add exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)
```

## Directory Structure

```
somastack/
├── README.md
├── Makefile                      # Common commands
├── docker-compose.yaml           # Full stack for local dev
├── docker-compose.standalone.yaml # Minimal for single service
│
├── config/                       # Configuration files
│   ├── kafka/
│   │   └── topics.yaml
│   ├── flink/
│   │   └── flink-conf.yaml
│   ├── temporal/
│   │   └── dynamicconfig.yaml
│   ├── kong/
│   │   └── kong.yaml
│   ├── postgres/
│   │   └── init/
│   │       ├── 01-databases.sql
│   │       ├── 02-events.sql
│   │       └── 03-sagas.sql
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── dashboards/
│   │       └── datasources/
│   ├── loki/
│   │   └── loki-config.yaml
│   └── opa/
│       └── policies/
│           └── authz.rego
│
├── helm/                         # Kubernetes deployment
│   └── somastack/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-dev.yaml
│       ├── values-staging.yaml
│       ├── values-prod.yaml
│       └── charts/
│           └── ...
│
├── terraform/                    # AWS infrastructure
│   ├── modules/
│   │   ├── eks/
│   │   ├── msk/
│   │   ├── rds/
│   │   └── elasticache/
│   ├── environments/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── main.tf
│
├── src/                          # Shared Python library
│   └── soma_common/
│       ├── __init__.py
│       ├── events/
│       │   ├── __init__.py
│       │   ├── store.py
│       │   ├── models.py
│       │   └── schemas.py
│       ├── sagas/
│       │   ├── __init__.py
│       │   ├── orchestrator.py
│       │   └── models.py
│       ├── tracing/
│       │   ├── __init__.py
│       │   ├── tracer.py
│       │   └── decorators.py
│       ├── logging/
│       │   ├── __init__.py
│       │   └── formatters.py
│       └── config/
│           ├── __init__.py
│           └── settings.py
│
├── cli/                          # CLI tool
│   └── somastack/
│       ├── __init__.py
│       ├── main.py
│       ├── commands/
│       │   ├── up.py
│       │   ├── down.py
│       │   ├── status.py
│       │   ├── events.py
│       │   ├── saga.py
│       │   └── dlq.py
│       └── utils/
│
├── flink-jobs/                   # Flink streaming jobs
│   ├── saga-orchestrator/
│   ├── event-replay/
│   └── dlq-processor/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── chaos/
│
└── docs/
    ├── architecture.md
    ├── deployment.md
    ├── operations.md
    └── troubleshooting.md
```

## Summary

This design provides a complete, production-grade platform for the Soma AI Agent Ecosystem with:

1. **Three Deployment Modes**: Standalone → SomaStack → Production
2. **15GB RAM Budget**: Carefully allocated across all components
3. **100% Open Source**: No vendor lock-in
4. **Event Sourcing**: Full audit trail, replay capability
5. **Saga Pattern**: Distributed transactions with compensation
6. **Observability**: Tracing, metrics, logging with beautiful output
7. **Security**: mTLS, OPA policies, secrets management
8. **Kubernetes Ready**: Helm charts for one-click deployment
9. **AWS Compatible**: Terraform modules for managed services
10. **Developer Experience**: CLI tools, decorators, shared library

The "chain reaction" architecture enables components to work independently or together, scaling from a developer laptop to millions of transactions in production.
