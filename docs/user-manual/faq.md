# Frequently Asked Questions

**Purpose**: Answer common questions about SomaBrain installation, usage, and troubleshooting.

**Audience**: End-users, developers, and system administrators using SomaBrain.

**Prerequisites**: Basic familiarity with SomaBrain concepts from [Quick Start Tutorial](quick-start-tutorial.md).

---

## Installation & Setup

### Q: What are the minimum system requirements?

**A**:
- **CPU**: 2+ cores recommended (ARM64 or x86_64)
- **RAM**: 4GB minimum, 8GB+ recommended for production
- **Storage**: 2GB for Docker images + data storage
- **OS**: Linux, macOS, or Windows with Docker support
- **Network**: Outbound internet access for Docker images

**Reference**: See [Installation Guide](installation.md) for detailed requirements.

### Q: Can I run SomaBrain without Docker?

**A**: Not recommended. SomaBrain requires multiple services (Redis, PostgreSQL, Kafka, OPA) with specific configurations. The Docker Compose setup ensures proper service coordination and networking.

**Alternative**: For development only, you can run individual components manually, but this requires extensive configuration expertise.

### Q: Why does installation fail with "permission denied"?

**A**: Common Docker permission issues:

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# On macOS, ensure Docker Desktop is running
# On Windows, run PowerShell as Administrator
```

**Verification**: Run `docker ps` without `sudo` - should not show permission error.

### Q: How do I check if SomaBrain is running correctly?

**A**: Use the health check endpoint:

```bash
curl http://localhost:9696/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "components": {
    "redis": {"status": "healthy"},
    "postgres": {"status": "healthy"},
    "kafka": {"status": "healthy"}
  }
}
```

---

## Memory Operations

### Q: What's the difference between SomaBrain and a regular database?

**A**: Key differences:

| Feature | Traditional Database | SomaBrain |
|---------|---------------------|-----------|
| Search Type | Exact keyword matching | Semantic similarity |
| Query Language | SQL, NoSQL syntax | Natural language |
| Data Structure | Fixed schemas | Flexible content + metadata |
| Relationships | Manual foreign keys | Automatic semantic connections |
| Use Case | Structured data storage | Contextual memory and reasoning |

### Q: Why are my similarity scores always low (< 0.3)?

**A**: Common causes and solutions:

1. **Insufficient content**: Store more descriptive memories
   ```json
   // Instead of: {"content": "Python good"}
   {"content": "Python is my favorite language because of its readable syntax and rich ML ecosystem"}
   ```

2. **Language mismatch**: Query and stored content should use similar vocabulary

3. **Cold start**: With few memories, semantic relationships are limited

**Verification**: Try querying for content you know exists with exact phrases first.

### Q: How many memories can SomaBrain handle?

**A**: Scalability limits:

- **Single Instance**: 1M+ memories with 8GB RAM
- **Production**: 10M+ memories with proper hardware scaling
- **Performance**: Search remains sub-second up to ~100K memories

**Reference**: See [Technical Manual - Capacity Planning](../technical-manual/architecture.md#capacity-planning).

### Q: Can I delete or update stored memories?

**A**: Yes, but with important considerations:

```bash
# Delete memory by ID
curl -X DELETE http://localhost:9696/memories/{memory_id}

# Update memory content (creates new version)
curl -X PUT http://localhost:9696/memories/{memory_id} \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated content", "metadata": {...}}'
```

**Note**: Updates create new semantic encodings, so similarity relationships may change.

### Q: What happens if I store duplicate content?

**A**: SomaBrain allows duplicates by design - memories with identical content but different metadata/context serve different purposes. Use metadata filtering to distinguish them.

---

## API Integration

### Q: Can I use SomaBrain with languages other than Python?

**A**: Yes! SomaBrain provides REST APIs accessible from any language:

- **JavaScript/Node.js**: Use `fetch()` or `axios`
- **Python**: Use `requests` or the official SDK
- **Java**: Use `OkHttp` or `RestTemplate`
- **Go**: Use standard `net/http`
- **cURL**: For command-line testing

**Reference**: See [API Integration Guide](features/api-integration.md) for language-specific examples.

### Q: How do I handle authentication?

**A**: SomaBrain supports multiple auth methods:

```bash
# API key authentication (recommended)
curl -H "X-API-Key: your-api-key" http://localhost:9696/recall

# JWT token authentication
curl -H "Authorization: Bearer your-jwt-token" http://localhost:9696/recall
```

**Configuration**: Set `SOMABRAIN_AUTH_MODE` environment variable in docker-compose.yml.

### Q: What's the maximum request size?

**A**: Default limits:

- **Content**: 1MB per memory
- **Metadata**: 64KB per memory
- **Batch Operations**: 100 memories per request

**Customization**: Modify `MAX_CONTENT_SIZE` in config/sandbox.tenants.yaml.

### Q: How do I handle rate limiting?

**A**: Default rate limits:

- **Free tier**: 100 requests/minute
- **Production**: Configurable per tenant

**Best Practices**:
- Implement exponential backoff
- Cache frequent queries locally
- Use batch operations when possible

---

## Multi-Tenant & Deployment

### Q: Can multiple users share one SomaBrain instance?

**A**: Yes, using tenant isolation:

```bash
# Store memory for specific tenant
curl -X POST http://localhost:9696/remember \
  -H "X-Tenant-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{"content": "User-specific memory"}'

# Query respects tenant boundaries
curl -X POST http://localhost:9696/recall \
  -H "X-Tenant-ID: user123" \
  -d '{"query": "my memories"}'
```

**Reference**: See [Multi-Tenant Usage Guide](features/multi-tenant-usage.md).

### Q: How do I backup my memories?

**A**: Multiple backup strategies:

```bash
# Database backup (PostgreSQL)
docker exec somabrain-postgres pg_dump -U postgres somabrain > backup.sql

# Memory export (JSON format)
curl -H "X-Tenant-ID: your-tenant" \
     http://localhost:9696/export > memories_backup.json

# Full Docker volume backup
docker run --rm -v somabrain_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data
```

**Verification**: Test restore procedures regularly.

### Q: How do I monitor SomaBrain in production?

**A**: Built-in monitoring endpoints:

```bash
# Metrics for Prometheus
curl http://localhost:9696/metrics

# Performance statistics
curl http://localhost:9696/stats

# Memory usage by tenant
curl http://localhost:9696/admin/tenants
```

**Reference**: See [Technical Manual - Monitoring](../technical-manual/monitoring.md).

---

## Performance & Troubleshooting

### Q: Why are my queries slow (> 5 seconds)?

**A**: Common performance issues:

1. **Resource constraints**: Check Docker memory/CPU limits
2. **Large result sets**: Use `k` parameter to limit results
3. **Complex metadata filters**: Optimize filter combinations
4. **Cold cache**: First queries after restart are slower

**Diagnostic Steps**:
```bash
# Check resource usage
docker stats somabrain-api somabrain-redis somabrain-postgres

# Profile slow queries
curl -X POST http://localhost:9696/recall?profile=true \
  -d '{"query": "your query", "k": 10}'
```

### Q: What does "Redis connection failed" mean?

**A**: Redis connectivity issues:

```bash
# Check Redis container status
docker compose ps redis

# Check Redis logs
docker compose logs redis

# Test Redis connection directly
docker exec -it somabrain-redis redis-cli ping
```

**Common Solutions**:
- Restart Redis: `docker compose restart redis`
- Check port conflicts: `netstat -tulpn | grep 6379`
- Verify Docker network: `docker network ls`

### Q: How do I debug memory encoding issues?

**A**: Enable debug logging:

```bash
# Set debug environment variable
export SOMABRAIN_LOG_LEVEL=DEBUG
docker compose up -d

# Check encoding logs
docker compose logs api | grep "encoding"
```

**Debug Information**:
- Vector dimensions and norms
- Encoding processing time
- Similarity computation details

### Q: Can I run SomaBrain on Apple Silicon (M1/M2)?

**A**: Yes, SomaBrain supports ARM64 architecture:

```bash
# Verify platform
docker compose --profile arm64 up -d

# Check image architecture
docker image inspect somabrain/api:latest | grep Architecture
```

**Note**: Initial image pull may take longer on ARM64 due to cross-compilation.

---

## Data & Privacy

### Q: Where is my data stored?

**A**: Data storage locations:

- **Memory Content**: PostgreSQL database in Docker volume
- **Vector Encodings**: Redis memory + optional persistence
- **Metadata**: PostgreSQL with indexed JSON columns
- **Logs**: Docker container logs + optional external logging

**Local Storage**: All data stays on your machine by default - no cloud transmission.

### Q: Is my data encrypted?

**A**: Encryption options:

- **At Rest**: Configure PostgreSQL encryption (TDE) and Redis encryption
- **In Transit**: Enable HTTPS/TLS for API endpoints
- **Application Level**: Encrypt sensitive content before storing

**Configuration**: See [Security Guide](../technical-manual/security/secrets-policy.md).

### Q: Can I export all my data?

**A**: Multiple export formats:

```bash
# JSON export (preserves metadata)
curl -H "X-Tenant-ID: your-tenant" \
     http://localhost:9696/export?format=json > export.json

# CSV export (for analysis)
curl http://localhost:9696/export?format=csv > export.csv

# Vector export (for migration)
curl http://localhost:9696/export?format=vectors > vectors.npy
```

**Verification**: Exports include all memories, metadata, and creation timestamps.

### Q: How do I migrate between SomaBrain instances?

**A**: Migration process:

1. **Export** from source instance (see above)
2. **Import** to target instance:
   ```bash
   curl -X POST http://new-instance:9696/import \
     -F "file=@export.json" \
     -H "X-Tenant-ID: your-tenant"
   ```
3. **Verify** memory counts match

**Reference**: See [Technical Manual - Backup and Recovery](../technical-manual/backup-and-recovery.md).

---

## Advanced Usage

### Q: Can I customize the similarity scoring algorithm?

**A**: Yes, through configuration:

```yaml
# config/sandbox.tenants.yaml
scoring:
  cosine_weight: 0.6        # Semantic similarity
  recency_weight: 0.15      # Time-based scoring
  frequency_weight: 0.25    # Diversity factor
  custom_boosts:            # Custom metadata boosting
    priority: 1.2
    confidence: 1.1
```

**Restart Required**: Changes require service restart to take effect.

### Q: How do I implement custom memory filtering?

**A**: Advanced filtering examples:

```bash
# Date range filtering
curl -X POST http://localhost:9696/recall \
  -d '{
    "query": "recent projects",
    "filters": {
      "date_after": "2025-01-01",
      "date_before": "2025-12-31"
    }
  }'

# Complex metadata filtering
curl -X POST http://localhost:9696/recall \
  -d '{
    "query": "technical knowledge",
    "filters": {
      "category": ["technical", "learning"],
      "confidence": {"$gte": 0.8},
      "tags": {"$contains": "python"}
    }
  }'
```

### Q: Can I create memory relationships manually?

**A**: Yes, using explicit relationship metadata:

```json
{
  "content": "Completed user authentication feature",
  "metadata": {
    "project": "webapp_v2",
    "relates_to": ["mem_login_system", "mem_security_audit"],
    "relationship_type": "completion",
    "sequence": 3
  }
}
```

**Query Relationships**:
```bash
curl -X POST http://localhost:9696/recall \
  -d '{
    "query": "authentication progress",
    "expand_relationships": true
  }'
```

---

## Getting Help

### Q: Where can I find more documentation?

**A**: Additional resources:

- **User Guides**: `/docs/user-manual/` directory
- **Technical Documentation**: `/docs/technical-manual/` directory
- **Development Info**: `/docs/development-manual/` directory
- **API Reference**: [API Integration Guide](features/api-integration.md)

### Q: How do I report bugs or request features?

**A**:

1. **Check Logs**: `docker compose logs api | tail -100`
2. **Search Issues**: Check existing GitHub issues first
3. **Create Issue**: Include system info, logs, and reproduction steps
4. **Feature Requests**: Describe use case and expected behavior

### Q: Is there a community forum?

**A**: Community resources:

- **GitHub Discussions**: For general questions and use cases
- **Technical Issues**: GitHub Issues tracker
- **Development Chat**: Slack/Discord (see project README)

### Q: How do I contribute to SomaBrain?

**A**: Contribution process:

1. **Read**: [Development Manual](../development-manual/index.md)
2. **Setup**: Local development environment
3. **Code**: Follow coding standards and testing guidelines
4. **Submit**: Pull request with tests and documentation

**Reference**: See [Contribution Process](../development-manual/contribution-process.md).

---

## Error Reference

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Redis connection timeout` | Redis overloaded or down | Restart Redis, check memory limits |
| `PostgreSQL connection refused` | Database not started | `docker compose up postgres -d` |
| `Memory encoding failed` | Invalid content format | Check content encoding (UTF-8) |
| `Tenant not found` | Missing tenant configuration | Add tenant to config/sandbox.tenants.yaml |
| `Rate limit exceeded` | Too many requests | Implement backoff, increase limits |
| `Memory not found` | Invalid memory ID | Check ID format and tenant scope |
| `Similarity threshold too low` | No matching memories | Lower threshold or add more memories |
| `Metadata validation failed` | Invalid metadata format | Check JSON schema compliance |

**Common Errors**: See individual feature guides for specific troubleshooting.

**References**:
- [Installation Guide](installation.md) for setup issues
- [Technical Manual](../technical-manual/index.md) for system administration
- [Development Manual](../development-manual/index.md) for code-related problems