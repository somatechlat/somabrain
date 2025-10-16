# Multi-Tenant Usage Guide

**Purpose**: Guide for configuring and managing SomaBrain in multi-tenant environments where multiple users or organizations share the same instance.

**Audience**: System administrators, DevOps engineers, and developers implementing SomaBrain for multiple users.

**Prerequisites**: SomaBrain installation complete and familiarity with [Memory Operations](memory-operations.md).

---

## Multi-Tenancy Overview

SomaBrain supports **multi-tenant architecture** that provides complete data isolation between different users, organizations, or applications while sharing the same underlying infrastructure:

### Key Benefits

**Data Isolation**: Each tenant's memories are completely isolated with no cross-tenant access possible.

**Resource Sharing**: Efficient resource utilization by sharing compute, storage, and network infrastructure.

**Centralized Management**: Single SomaBrain instance serves multiple tenants with unified monitoring and administration.

**Scalable Onboarding**: Add new tenants without infrastructure changes or service restarts.

**Cost Efficiency**: Shared infrastructure reduces per-tenant costs while maintaining security boundaries.

### Tenant Architecture

```
SomaBrain Instance
├── Tenant A (org_acme)
│   ├── Memory Store (isolated)
│   ├── Vector Encodings (isolated)  
│   └── Configuration (tenant-specific)
├── Tenant B (user_alice)
│   ├── Memory Store (isolated)
│   ├── Vector Encodings (isolated)
│   └── Configuration (tenant-specific)  
└── Shared Components
    ├── API Gateway (routing)
    ├── Authentication (unified)
    └── System Resources (Redis, PostgreSQL)
```

**Isolation Levels**:
- **Data**: Complete memory content and metadata isolation
- **Vector Space**: Separate vector encodings per tenant  
- **Configuration**: Tenant-specific settings and limits
- **Metrics**: Per-tenant usage and performance monitoring

---

## Tenant Configuration

### Tenant Definition

Configure tenants in the main configuration file:

```yaml
# config/sandbox.tenants.yaml
tenants:
  org_acme:
    name: "ACME Corporation"
    type: "organization"
    status: "active"
    created_at: "2025-01-15T00:00:00Z"
    
    # Resource limits
    limits:
      max_memories: 1000000
      max_storage_mb: 5120  # 5GB
      requests_per_minute: 1000
      concurrent_requests: 50
      
    # Memory configuration
    memory:
      vector_dimensions: 1024
      similarity_threshold: 0.2
      max_content_length: 10240  # 10KB
      
    # Feature flags  
    features:
      cognitive_reasoning: true
      batch_operations: true
      export_capabilities: true
      advanced_analytics: true
      
    # Authentication
    auth:
      api_keys: 
        - key_id: "acme_prod_001" 
          key: "sk_acme_prod_abc123xyz"
          scopes: ["read", "write", "admin"]
        - key_id: "acme_readonly_001"
          key: "sk_acme_ro_def456uvw" 
          scopes: ["read"]
          
  user_alice:
    name: "Alice Developer"
    type: "individual"
    status: "active" 
    created_at: "2025-02-01T00:00:00Z"
    
    # Individual user limits (smaller)  
    limits:
      max_memories: 10000
      max_storage_mb: 100  # 100MB
      requests_per_minute: 100
      concurrent_requests: 5
      
    memory:
      vector_dimensions: 512  # Smaller for individual use
      similarity_threshold: 0.3
      max_content_length: 2048  # 2KB
      
    features:
      cognitive_reasoning: false  # Disabled for free tier
      batch_operations: true
      export_capabilities: true
      advanced_analytics: false
      
    auth:
      api_keys:
        - key_id: "alice_personal_001"
          key: "sk_alice_personal_ghi789rst"
          scopes: ["read", "write"]

# Global defaults for new tenants          
defaults:
  limits:
    max_memories: 1000
    max_storage_mb: 10
    requests_per_minute: 60
    concurrent_requests: 3
    
  memory:
    vector_dimensions: 384
    similarity_threshold: 0.4
    max_content_length: 1024
    
  features:
    cognitive_reasoning: false
    batch_operations: false 
    export_capabilities: true
    advanced_analytics: false
```

**Verification**: Restart SomaBrain services after configuration changes: `docker compose restart`

### Dynamic Tenant Management

Add tenants via API without service restart:

```bash
# Create new tenant
curl -X POST http://localhost:9696/admin/tenants \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "tenant_id": "startup_beta", 
    "name": "Beta Startup Inc",
    "type": "organization",
    "limits": {
      "max_memories": 50000,
      "max_storage_mb": 500,
      "requests_per_minute": 500
    },
    "features": {
      "cognitive_reasoning": true,
      "batch_operations": true
    }
  }'

# Update existing tenant configuration
curl -X PUT http://localhost:9696/admin/tenants/startup_beta \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "limits": {
      "max_memories": 100000,
      "requests_per_minute": 1000
    }
  }'

# List all tenants
curl -H "X-Admin-Key: your-admin-key" \
     http://localhost:9696/admin/tenants
```

**Response**:
```json
{
  "tenants": [
    {
      "tenant_id": "org_acme",
      "name": "ACME Corporation", 
      "status": "active",
      "memory_count": 45230,
      "storage_used_mb": 2341,
      "last_activity": "2025-10-15T14:30:00Z"
    }
  ]
}
```

---

## Tenant Authentication and Access Control

### API Key Management

Each tenant can have multiple API keys with different scopes:

```bash
# Generate new API key for tenant
curl -X POST http://localhost:9696/admin/tenants/org_acme/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "key_id": "acme_analytics_001",
    "scopes": ["read", "analytics"],
    "expires_at": "2026-01-01T00:00:00Z",
    "description": "Analytics team read-only access"
  }'

# Revoke API key  
curl -X DELETE http://localhost:9696/admin/tenants/org_acme/keys/acme_analytics_001 \
  -H "X-Admin-Key: your-admin-key"

# List tenant API keys
curl -H "X-Admin-Key: your-admin-key" \
     http://localhost:9696/admin/tenants/org_acme/keys
```

**API Key Scopes**:
- `read`: Memory recall and search operations
- `write`: Memory storage and updates  
- `delete`: Memory deletion operations
- `admin`: Tenant configuration changes
- `analytics`: Usage metrics and statistics
- `export`: Data export capabilities

### JWT Token Authentication

Alternative authentication using JWT tokens:

```bash
# Configure JWT authentication in docker-compose.yml
environment:
  - SOMABRAIN_AUTH_MODE=jwt
  - SOMABRAIN_JWT_SECRET=your-jwt-signing-secret
  - SOMABRAIN_JWT_ALGORITHM=HS256
```

**JWT Token Structure**:
```json
{
  "tenant_id": "org_acme",
  "user_id": "user_123", 
  "scopes": ["read", "write"],
  "exp": 1735689600,
  "iat": 1735603200
}
```

**Usage Example**:
```bash
# Generate JWT token (your application)
jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Use JWT token in requests
curl -X POST http://localhost:9696/remember \
  -H "Authorization: Bearer $jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User-specific memory content",
    "metadata": {"user_id": "user_123"}
  }'
```

### Role-Based Access Control (RBAC)

Define roles and permissions per tenant:

```yaml
# config/tenant_rbac.yaml
tenants:
  org_acme:
    roles:
      admin:
        permissions: ["*"]  # All permissions
        users: ["admin@acme.com"]
        
      developer: 
        permissions: ["read", "write", "analytics"]
        users: ["dev1@acme.com", "dev2@acme.com"]
        
      analyst:
        permissions: ["read", "analytics"] 
        users: ["analyst@acme.com"]
        
      readonly:
        permissions: ["read"]
        users: ["guest@acme.com"]
        
    # Permission definitions
    permissions:
      read: ["GET /recall", "GET /memories/*", "GET /search"]
      write: ["POST /remember", "PUT /memories/*", "POST /remember/batch"]
      delete: ["DELETE /memories/*"]  
      analytics: ["GET /metrics", "GET /admin/stats"]
      admin: ["POST /admin/*", "PUT /admin/*", "DELETE /admin/*"]
```

---

## Tenant-Specific Operations

### Memory Operations with Tenant Context

All memory operations are automatically scoped to the authenticated tenant:

```bash
# Store memory - automatically isolated to tenant
curl -X POST http://localhost:9696/remember \
  -H "X-API-Key: sk_acme_prod_abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ACME internal process documentation",
    "metadata": {
      "department": "engineering",
      "classification": "internal",
      "project": "project_alpha"  
    }
  }'

# Recall memories - only searches within tenant scope
curl -X POST http://localhost:9696/recall \
  -H "X-API-Key: sk_acme_prod_abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "project alpha documentation", 
    "k": 10,
    "filters": {
      "department": "engineering"
    }
  }'
```

**Automatic Isolation**: The API automatically adds tenant filtering to all queries, ensuring complete data isolation.

### Tenant-Specific Configuration Overrides

Override global settings per tenant:

```bash
# Configure tenant-specific similarity scoring
curl -X PUT http://localhost:9696/admin/tenants/org_acme/config \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "similarity_scoring": {
      "cosine_weight": 0.7,
      "recency_weight": 0.2, 
      "frequency_weight": 0.1
    },
    "vector_encoding": {
      "model": "sentence-transformers/all-MiniLM-L6-v2",
      "dimensions": 1024
    },
    "memory_limits": {
      "max_content_length": 8192,
      "max_metadata_size": 2048
    }
  }'
```

### Cross-Tenant Operations (Admin Only)

Administrative operations across multiple tenants:

```bash
# Search across all tenants (admin operation)
curl -X POST http://localhost:9696/admin/search/global \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "query": "security vulnerability",
    "tenant_filter": ["org_acme", "startup_beta"],
    "k": 5,
    "include_tenant_info": true
  }'

# Cross-tenant memory statistics  
curl -H "X-Admin-Key: your-admin-key" \
     http://localhost:9696/admin/stats/cross-tenant?metric=memory_growth
```

---

## Resource Management and Limits

### Memory and Storage Limits

Monitor and enforce tenant resource usage:

```bash
# Check tenant resource usage
curl -H "X-Admin-Key: your-admin-key" \
     http://localhost:9696/admin/tenants/org_acme/usage

# Response with usage metrics
{
  "tenant_id": "org_acme",
  "usage": {
    "memory_count": 45230,
    "storage_used_mb": 2341,
    "storage_limit_mb": 5120,  
    "storage_percentage": 45.7,
    "vector_index_size_mb": 890,
    "metadata_size_mb": 1451
  },
  "limits": {
    "max_memories": 1000000,
    "memories_percentage": 4.5,
    "approaching_limits": []
  }
}
```

### Rate Limiting Per Tenant

Configure and monitor API rate limits:

```yaml
# Rate limiting configuration
rate_limits:
  org_acme:
    requests_per_minute: 1000
    burst_capacity: 50
    concurrent_requests: 50
    
  user_alice:
    requests_per_minute: 100
    burst_capacity: 10
    concurrent_requests: 5
    
# Rate limit algorithms
algorithms:
  sliding_window: 
    window_size: 60  # seconds
    precision: 10    # sub-windows
    
  token_bucket:
    refill_rate: 16.67  # tokens per second (1000/60)
    bucket_size: 50
```

**Rate Limit Headers**:
```bash
# API responses include rate limit headers
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1635724800
X-RateLimit-Retry-After: 23
```

### Auto-scaling Based on Tenant Usage

Configure automatic resource scaling:

```bash
# Set up tenant auto-scaling rules
curl -X PUT http://localhost:9696/admin/tenants/org_acme/scaling \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "rules": [
      {
        "metric": "memory_usage_percentage",
        "threshold": 80,
        "action": "increase_storage_limit",
        "parameters": {"increase_by_mb": 1024}
      },
      {
        "metric": "requests_per_minute", 
        "threshold": 900,
        "action": "increase_rate_limit",
        "parameters": {"new_limit": 1500}
      }
    ],
    "notifications": {
      "webhook_url": "https://acme.com/webhooks/somabrain",
      "email": ["admin@acme.com"]
    }
  }'
```

---

## Tenant Monitoring and Analytics

### Per-Tenant Metrics

Monitor tenant-specific performance and usage:

```bash
# Get tenant performance metrics
curl -H "X-Admin-Key: your-admin-key" \
     "http://localhost:9696/admin/tenants/org_acme/metrics?period=24h"

# Response with detailed metrics
{
  "tenant_id": "org_acme",
  "period": "24h",
  "metrics": {
    "requests": {
      "total": 12450,
      "successful": 12380,
      "failed": 70,
      "success_rate": 99.44
    },
    "operations": {
      "remember": 8200,
      "recall": 4100,
      "reason": 150
    },
    "performance": {
      "avg_response_time_ms": 45,
      "p95_response_time_ms": 120,
      "p99_response_time_ms": 230
    },
    "memory": {
      "new_memories": 8200,
      "total_memories": 45230, 
      "avg_similarity_score": 0.73
    }
  }
}
```

### Usage Analytics Dashboard

Export metrics for external dashboards:

```bash
# Prometheus metrics endpoint (per tenant)
curl -H "X-Admin-Key: your-admin-key" \
     http://localhost:9696/metrics/tenant/org_acme

# Sample Prometheus metrics
# TYPE somabrain_memories_total counter
somabrain_memories_total{tenant="org_acme"} 45230

# TYPE somabrain_requests_total counter  
somabrain_requests_total{tenant="org_acme",operation="recall"} 4100

# TYPE somabrain_response_time_seconds histogram
somabrain_response_time_seconds_bucket{tenant="org_acme",le="0.1"} 8900
somabrain_response_time_seconds_bucket{tenant="org_acme",le="0.5"} 12100
```

### Tenant Health Monitoring

Monitor tenant health and detect issues:

```bash
# Tenant health check
curl -H "X-Admin-Key: your-admin-key" \
     http://localhost:9696/admin/tenants/org_acme/health

# Health status response  
{
  "tenant_id": "org_acme",
  "health_status": "healthy",  # healthy, warning, critical
  "checks": {
    "memory_storage": {
      "status": "healthy",
      "usage_percentage": 45.7
    },
    "rate_limits": {
      "status": "healthy", 
      "current_usage": 67.3
    },
    "api_errors": {
      "status": "warning",
      "error_rate": 0.56,
      "threshold": 0.5
    },
    "response_time": {
      "status": "healthy",
      "avg_ms": 45,
      "p95_ms": 120
    }
  },
  "recommendations": [
    "Error rate slightly elevated - investigate failed requests",
    "Consider increasing rate limits for peak usage periods"
  ]
}
```

---

## Data Export and Migration

### Tenant Data Export

Export tenant data for backup or migration:

```bash
# Export all tenant memories
curl -H "X-Admin-Key: your-admin-key" \
     "http://localhost:9696/admin/tenants/org_acme/export?format=json" > acme_backup.json

# Export with filters
curl -H "X-Admin-Key: your-admin-key" \
     -G "http://localhost:9696/admin/tenants/org_acme/export" \
     -d "format=json" \
     -d "date_after=2025-01-01" \
     -d "category=technical_knowledge" > acme_filtered_backup.json

# Export in different formats
curl -H "X-Admin-Key: your-admin-key" \
     "http://localhost:9696/admin/tenants/org_acme/export?format=csv" > acme_memories.csv
```

**Export Formats**:
- `json`: Complete memory data with metadata and timestamps
- `csv`: Tabular format for analysis
- `jsonl`: JSON Lines for streaming processing
- `parquet`: Compressed columnar format for analytics

### Tenant Data Import

Import data into tenant (migration scenarios):

```bash
# Import from JSON export
curl -X POST http://localhost:9696/admin/tenants/org_acme/import \
  -H "Content-Type: multipart/form-data" \
  -H "X-Admin-Key: your-admin-key" \
  -F "file=@acme_backup.json" \
  -F "import_mode=merge" \
  -F "conflict_resolution=update"

# Import with validation
curl -X POST http://localhost:9696/admin/tenants/org_acme/import \
  -H "X-Admin-Key: your-admin-key" \
  -F "file=@migration_data.json" \
  -F "validate_only=true"  # Dry run
```

**Import Modes**:
- `merge`: Add new memories, update existing ones
- `replace`: Replace all tenant data 
- `append`: Add new memories only, skip conflicts

### Cross-Instance Migration

Migrate tenants between SomaBrain instances:

```bash
# 1. Export from source instance
curl -H "X-Admin-Key: source-admin-key" \
     http://source.somabrain.com:9696/admin/tenants/org_acme/export?format=complete > complete_export.json

# 2. Create tenant on target instance  
curl -X POST http://target.somabrain.com:9696/admin/tenants \
  -H "X-Admin-Key: target-admin-key" \
  -d '@tenant_config.json'

# 3. Import data to target instance
curl -X POST http://target.somabrain.com:9696/admin/tenants/org_acme/import \
  -H "X-Admin-Key: target-admin-key" \
  -F "file=@complete_export.json" \
  -F "import_mode=replace"

# 4. Verify migration
curl -H "X-Admin-Key: target-admin-key" \
     http://target.somabrain.com:9696/admin/tenants/org_acme/stats
```

---

## Security and Isolation

### Data Isolation Verification

Verify tenant data isolation is working correctly:

```bash
# Test cross-tenant access prevention
curl -X POST http://localhost:9696/recall \
  -H "X-API-Key: sk_alice_personal_ghi789rst" \  # Alice's key
  -H "Content-Type: application/json" \
  -d '{
    "query": "ACME internal documentation",  # Should find nothing
    "k": 10
  }'

# Expected response: Empty results (no cross-tenant access)
{
  "results": [],
  "message": "No memories found matching query"
}
```

### Network Security

Configure network-level isolation:

```yaml
# docker-compose.yml network configuration
networks:
  somabrain_internal:
    driver: bridge
    internal: true  # No external access
    
  somabrain_api:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
          
services:
  somabrain-api:
    networks:
      - somabrain_api
      - somabrain_internal
      
  somabrain-redis:
    networks:
      - somabrain_internal  # No direct external access
      
  somabrain-postgres:
    networks:
      - somabrain_internal  # No direct external access
```

### Encryption and Data Protection

Configure encryption for tenant data:

```bash
# Enable at-rest encryption in docker-compose.yml
environment:
  - POSTGRES_ENCRYPTION=on
  - POSTGRES_ENCRYPTION_KEY=your-encryption-key
  - REDIS_ENCRYPTION=on
  - SOMABRAIN_ENCRYPT_MEMORIES=true
  - SOMABRAIN_ENCRYPTION_KEY=your-memory-encryption-key
```

**Encryption Layers**:
- **Database**: PostgreSQL transparent data encryption (TDE)  
- **Cache**: Redis encryption for vector data
- **Application**: Memory content encryption before storage
- **Transport**: TLS/HTTPS for all API communications

---

## Troubleshooting Multi-Tenant Issues

### Common Multi-Tenant Problems

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Cross-tenant data leakage | User sees other tenants' data | Check tenant ID validation in API requests |
| Rate limit conflicts | Tenant hitting limits unexpectedly | Verify rate limit configuration per tenant |
| Authentication errors | API key rejected | Check tenant API key configuration and expiry |
| Resource exhaustion | Performance degradation | Monitor per-tenant resource usage |
| Configuration conflicts | Inconsistent behavior | Validate tenant-specific configuration |

### Debugging Tenant Issues

Enable detailed tenant-specific logging:

```bash
# Enable tenant debugging
curl -X PUT http://localhost:9696/admin/debug \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "tenant_id": "org_acme",
    "log_level": "DEBUG",
    "trace_requests": true,
    "trace_isolation": true
  }'

# Check tenant-specific logs
docker logs somabrain-api | grep "tenant=org_acme"
```

### Performance Monitoring

Monitor multi-tenant performance:

```bash
# Per-tenant performance metrics
curl -H "X-Admin-Key: your-admin-key" \
     http://localhost:9696/admin/performance/tenants

# Identify performance bottlenecks
curl -H "X-Admin-Key: your-admin-key" \
     "http://localhost:9696/admin/bottlenecks?period=1h&tenant=org_acme"
```

**Verification**: Multi-tenant setup is working correctly when tenants cannot access each other's data and resource limits are properly enforced.

---

**Common Errors**: See [FAQ](../faq.md) for multi-tenant troubleshooting.

**References**:
- [Installation Guide](../installation.md) for initial multi-tenant setup
- [API Integration Guide](api-integration.md) for tenant-aware API usage
- [Technical Manual - Security](../../technical-manual/security/rbac-matrix.md) for advanced security configuration  
- [Technical Manual - Monitoring](../../technical-manual/monitoring.md) for tenant monitoring setup