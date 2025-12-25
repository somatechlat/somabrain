# SRS-11: Docker Deployment Architecture

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible  
**Module:** Container Deployment Specification

---

## 1. Overview

Complete Docker deployment specification for the unified SomaBrain + SomaFractalMemory platform.

---

## 2. Service Architecture

```mermaid
flowchart TB
    subgraph External["External Access"]
        LB[Load Balancer / Nginx]
        UI[SomaBrain UI :80/443]
    end
    
    subgraph Apps["Application Layer"]
        SB[somabrain<br/>:9696]
        SFM[somafractalmemory<br/>:9595]
    end
    
    subgraph Auth["Authentication"]
        KC[keycloak<br/>:20880]
    end
    
    subgraph Billing["Billing"]
        LAGO[lago-api<br/>:3000]
        LAGO_WEB[lago-front<br/>:80]
    end
    
    subgraph Data["Data Layer"]
        PG[(postgres<br/>:5432)]
        Redis[(redis<br/>:6379)]
    end
    
    subgraph Vector["Vector Layer"]
        MV[(milvus<br/>:19530)]
        ETCD[etcd<br/>:2379]
        MINIO[minio<br/>:9000]
    end
    
    subgraph Streaming["Streaming"]
        KAFKA[kafka<br/>:9092]
        ZK[zookeeper<br/>:2181]
    end
    
    LB --> UI
    LB --> SB
    LB --> SFM
    
    SB --> PG
    SB --> Redis
    SB --> SFM
    SB --> KAFKA
    SB --> KC
    SB --> LAGO
    
    SFM --> PG
    SFM --> Redis
    SFM --> MV
    
    MV --> ETCD
    MV --> MINIO
    
    KAFKA --> ZK
```

---

## 3. Docker Compose Service Definitions

### 3.1 Core Services

| Service | Image | Ports | Depends On | Required |
|---------|-------|-------|------------|:--------:|
| `somabrain` | `somabrain:latest` | 9696 | postgres, redis | ✓ |
| `somafractalmemory` | `somafractalmemory:latest` | 9595 | postgres, redis, milvus | ✓ |
| `postgres` | `postgres:15` | 5432 | - | ✓ |
| `redis` | `redis:7-alpine` | 6379 | - | ✓ |

### 3.2 Vector Services

| Service | Image | Ports | Depends On | Required |
|---------|-------|-------|------------|:--------:|
| `milvus` | `milvusdb/milvus:v2.3.0` | 19530, 9091 | etcd, minio | ✓ |
| `etcd` | `quay.io/coreos/etcd:v3.5.5` | 2379 | - | ✓ |
| `minio` | `minio/minio:RELEASE.2023-03-20` | 9000, 9001 | - | ✓ |

### 3.3 Optional Services

| Service | Image | Ports | Depends On | Required |
|---------|-------|-------|------------|:--------:|
| `keycloak` | `quay.io/keycloak/keycloak:22.0` | 20880 | postgres | SSO |
| `lago-api` | `getlago/lago-api:v0.50.0` | 3000 | postgres, redis | Billing |
| `kafka` | `confluentinc/cp-kafka:7.4.0` | 9092 | zookeeper | Streaming |
| `zookeeper` | `confluentinc/cp-zookeeper:7.4.0` | 2181 | - | Streaming |

---

## 4. Resource Limits

### 4.1 Memory Allocation (16GB Total)

| Service | Memory Limit | Memory Request |
|---------|:------------:|:--------------:|
| somabrain | 2 GB | 1 GB |
| somafractalmemory | 1 GB | 512 MB |
| postgres | 2 GB | 1 GB |
| redis | 512 MB | 256 MB |
| milvus | 6 GB | 4 GB |
| etcd | 256 MB | 128 MB |
| minio | 512 MB | 256 MB |
| keycloak | 1 GB | 512 MB |
| lago-api | 1 GB | 512 MB |
| kafka | 1 GB | 512 MB |

### 4.2 CPU Allocation

| Service | CPU Limit | CPU Request |
|---------|:---------:|:-----------:|
| somabrain | 2.0 | 0.5 |
| somafractalmemory | 1.0 | 0.25 |
| postgres | 2.0 | 0.5 |
| redis | 0.5 | 0.1 |
| milvus | 4.0 | 1.0 |
| etcd | 0.5 | 0.1 |
| minio | 1.0 | 0.25 |

---

## 5. Network Configuration

### 5.1 Docker Networks

| Network | Driver | Purpose |
|---------|--------|---------|
| `soma-network` | bridge | Internal service communication |
| `soma-external` | bridge | External access (load balancer) |

### 5.2 Port Mapping

| External Port | Internal Port | Service |
|:-------------:|:-------------:|---------|
| 80 | 80 | nginx (UI) |
| 443 | 443 | nginx (HTTPS) |
| 9696 | 9696 | somabrain API |
| 9595 | 9595 | somafractalmemory API |
| 20880 | 8080 | keycloak |
| 3000 | 3000 | lago API |

---

## 6. Volume Definitions

| Volume | Container Path | Purpose |
|--------|----------------|---------|
| `postgres_data` | `/var/lib/postgresql/data` | Database persistence |
| `redis_data` | `/data` | Cache persistence |
| `milvus_data` | `/var/lib/milvus` | Vector index persistence |
| `minio_data` | `/data` | Object storage |
| `etcd_data` | `/etcd` | etcd persistence |

---

## 7. Environment Configuration

### 7.1 SomaBrain Environment

```env
# Core
SOMABRAIN_LOG_LEVEL=INFO
SOMABRAIN_JWT_SECRET=${JWT_SECRET}
SOMABRAIN_AUTH_REQUIRED=true

# Database
SOMABRAIN_POSTGRES_DSN=postgresql://soma:soma@postgres:5432/somabrain

# Redis
SOMABRAIN_REDIS_URL=redis://redis:6379/0

# Integration
SOMABRAIN_FRACTALMEMORY_URL=http://somafractalmemory:9595

# Auth
SOMABRAIN_AUTH_SERVICE_URL=http://keycloak:8080

# Billing
SOMABRAIN_LAGO_URL=http://lago-api:3000
```

### 7.2 SomaFractalMemory Environment

```env
# Core
SOMA_API_PORT=9595
SOMA_API_TOKEN=${API_TOKEN}
SOMA_LOG_LEVEL=INFO

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=soma
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=somamemory

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Milvus
SOMA_MILVUS_HOST=milvus
SOMA_MILVUS_PORT=19530
```

---

## 8. Health Checks

| Service | Endpoint | Interval | Timeout | Retries |
|---------|----------|:--------:|:-------:|:-------:|
| somabrain | `/health` | 30s | 10s | 3 |
| somafractalmemory | `/healthz` | 30s | 10s | 3 |
| postgres | `pg_isready` | 10s | 5s | 5 |
| redis | `redis-cli ping` | 10s | 5s | 3 |
| milvus | `:9091/healthz` | 30s | 10s | 3 |
| keycloak | `/health/ready` | 30s | 10s | 3 |

---

## 9. Startup Order

```mermaid
flowchart TD
    A[1. postgres] --> B[2. redis]
    B --> C[3. etcd]
    C --> D[4. minio]
    D --> E[5. milvus]
    E --> F[6. somafractalmemory]
    F --> G[7. somabrain]
    
    A --> H[3. keycloak]
    H --> G
    
    A --> I[3. lago-api]
    I --> G
    
    J[2. zookeeper] --> K[3. kafka]
    K --> G
```

---

## 10. Docker Compose Profiles

| Profile | Services Included | Use Case |
|---------|-------------------|----------|
| `core` | somabrain, sfm, postgres, redis, milvus | Minimum viable |
| `auth` | core + keycloak | With SSO |
| `billing` | core + lago | With billing |
| `streaming` | core + kafka | With events |
| `full` | All services | Complete production |

### Usage

```bash
# Core only
docker compose --profile core up -d

# With auth
docker compose --profile core --profile auth up -d

# Full production
docker compose --profile full up -d
```

---

## 11. Scaling Configuration

### 11.1 Horizontal Pod Autoscaling (K8s)

| Service | Min | Max | Target CPU |
|---------|:---:|:---:|:----------:|
| somabrain | 2 | 10 | 70% |
| somafractalmemory | 2 | 5 | 70% |

### 11.2 Docker Compose Scaling

```bash
docker compose up -d --scale somabrain=3 --scale somafractalmemory=2
```

---

*Docker Deployment Architecture - SomaBrain SaaS Platform*
