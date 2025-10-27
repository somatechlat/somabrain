# SomaBrain Changelog

**Purpose**: Chronological record of all changes, improvements, and fixes in SomaBrain releases.

**Audience**: Developers, operators, and users tracking version changes and compatibility.

**Prerequisites**: Understanding of semantic versioning (MAJOR.MINOR.PATCH).

---

## Version History

All notable changes to SomaBrain are documented in this file. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Format Legend
- 🚀 **Added** - New features and capabilities
- 🔧 **Changed** - Changes in existing functionality
- 🐛 **Fixed** - Bug fixes and error corrections
- 🔒 **Security** - Security vulnerability fixes
- ⚠️ **Deprecated** - Soon-to-be removed features
- 💥 **Removed** - Removed features
- 📚 **Documentation** - Documentation improvements

---

## [Unreleased]

### 🚀 Added
- Complete documentation restructure following 4-manual standard
- Comprehensive onboarding guide for new developers and agent coders
- Automated backup and recovery procedures
- Production-ready Kubernetes Helm charts
- Performance benchmarking suite with canonical test cases
 - Kafka teach feedback pipeline:
   - New Avro contracts: `teach_feedback.avsc`, `teach_capsule.avsc`
   - Processor service: `somabrain.services.teach_feedback_processor`
   - Topic: `cog.teach.feedback` → maps `rating` to `r_user` and publishes `RewardEvent`
   - Smoke script: `scripts/e2e_teach_feedback_smoke.py`

### 🔧 Changed
- Improved metrics bridge architecture for better package compatibility
- Enhanced strict-mode validation with clearer error messages
- Optimized memory client connection pooling for higher throughput

### 📚 Documentation
- Created User Manual with installation and feature guides
- Created Technical Manual with deployment and operational procedures
- Created Development Manual with coding standards and contribution process
- Created Onboarding Manual for new team members and contractors
- Added comprehensive runbooks for all major system components
 - Documented teach feedback pipeline in Technical Manual and User Manual

### 💥 Removed
- Legacy environment variants and overlays removed:
  - Dropped support for `.env.local` and other per-variant env files. Use a single canonical `.env`.
  - Deleted `docker-compose.9999.yml` and other overlay compose files. Single `docker-compose.yml` is the source of truth.

---

## [v0.1.0] - 2025-10-15

### 🚀 Added
- **Core Cognitive Memory Platform**: Complete hyperdimensional memory system
  - Binary hyperdimensional computing (BHDC) for semantic encoding
  - Density matrix tracking for memory relationship modeling
  - Multi-tenant working memory with isolated namespaces
  - Unified scoring combining cosine similarity, frequency-directions, and recency
- **Production FastAPI Service**: RESTful API with comprehensive endpoints
  - `POST /remember` - Store memories with semantic encoding and metadata
  - `POST /recall` - Retrieve memories using semantic similarity search
  - `POST /plan` - Generate reasoning plans based on stored knowledge
  - `GET /health` - Comprehensive health check aggregating all dependencies
  - `GET /metrics` - Prometheus metrics export for observability
- **Mathematical Correctness Framework**: Property testing and invariant validation
  - Density matrix trace normalization (abs(trace(ρ) - 1) < 1e-4)
  - Positive semi-definite (PSD) spectrum maintenance via eigenvalue clipping
  - BHDC binding/unbinding roundtrip accuracy validation
  - Scorer component weight bounds enforcement
- **Strict Real Mode**: Production-grade execution enforcement
  - `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1` disables all stub/mock code paths
  - Runtime audit system detecting and preventing stub usage
  - Comprehensive environment validation requiring real backing services
- **Multi-Service Architecture**: Containerized deployment with Docker Compose
  - Redis for high-performance working memory and caching
  - PostgreSQL for persistent metadata and audit log storage
  - Kafka for event streaming and audit trail (optional)
  - OPA policy engine for authorization and governance
  - Prometheus metrics collection and monitoring

### 🔧 Changed
- **Memory Client Architecture**: HTTP-first design with circuit breaker pattern
  - Write mirroring to ensure consistency across memory tiers
  - Configurable timeouts and retry policies for resilience
  - Outbox pattern for reliable event publishing
- **Configuration System**: Environment-based configuration with validation
  - Centralized settings through `common.config.Settings`
  - Support for `.env.local` files for local development
  - Dynamic port assignment for conflict-free local setup

### 🐛 Fixed
- **Metrics Package Conflicts**: Resolved import conflicts between stub and real metrics modules
  - Created bridge package (`somabrain/metrics/__init__.py`) for compatibility
  - Removed lightweight stub metrics that shadowed production implementation
  - Fixed `external_metrics_ready` and `metrics_endpoint` attribute errors in health checks

### 🔒 Security
- **JWT Authentication**: Configurable token-based authentication with OPA integration
- **Rate Limiting**: Per-tenant and global rate limits with burst handling
- **Audit Logging**: Comprehensive structured logging of all memory operations
- **Secrets Management**: Environment-based secret injection with validation

### 📚 Documentation
- **Architecture Documentation**: Complete system design with component interaction diagrams
- **API Documentation**: Interactive OpenAPI/Swagger documentation
- **Development Guide**: Local setup, coding standards, and contribution workflow
- **Operations Guide**: Deployment procedures, monitoring setup, and runbooks
- **Mathematical Documentation**: BHDC algorithms, density matrix operations, and invariants

### Infrastructure
- **Docker Support**: Multi-stage Dockerfile for production-ready container images
- **Docker Compose**: Complete local development stack with service orchestration
- **Kubernetes Ready**: Helm chart preparation for cloud-native deployment
- **CI/CD Pipeline**: Automated testing, linting, and quality gates
- **Monitoring Stack**: Prometheus metrics and alerting rules

### Launch Snapshot

```bash
docker run --rm \
  -p 8000:9696 \
  -e SOMABRAIN_DISABLE_AUTH=true \
  ghcr.io/somatechlat/somabrain:latest
```

- Health: `curl -s http://localhost:8000/health`
- OpenAPI: `http://localhost:8000/docs`
- Metrics: `http://localhost:8000/metrics`

**Endpoints**: `/remember`, `/recall`, `/link`, `/docs`, `/metrics`

**Security**: Token auth via `Authorization: Bearer <token>` (set `SOMABRAIN_API_TOKEN` to enable). Tenancy via `X-Tenant-ID`. For demos you may keep `SOMABRAIN_DISABLE_AUTH=true`; enable auth for real deployments.

**Observability**:

```bash
docker compose -f docker-compose.observability.yml up
```

- Prometheus UI: `http://localhost:9090`

**Known Limits**:
- Bounded working memory; tune dimensions through environment variables.
- Apply rate/size limits at the edge proxy for public deployments.

---

## [v0.0.1] - 2024-12-01 (Initial Research Release)

### 🚀 Added
- **Mathematical Foundations**: Core hyperdimensional computing algorithms
  - BHDC binding and unbinding operations
  - Permutation-based role generation for deterministic encoding
  - Frequency-directions salience sketching for diversity-aware recall
- **Proof of Concept API**: Basic FastAPI service demonstrating core concepts
- **Property Testing Framework**: Mathematical invariant validation using hypothesis
- **Basic Memory Operations**: Simple store/retrieve functionality for validation

### 📚 Documentation
- **Research Documentation**: Mathematical foundations and algorithm descriptions
- **Proof of Concept**: Demonstration of core hyperdimensional computing principles

---

## Migration Guides

### Upgrading from v0.0.x to v0.1.0

This is a major release with breaking changes. Follow this migration guide:

#### Configuration Changes
```bash
# Old environment variables (deprecated)
SOMABRAIN_REDIS_HOST=localhost
SOMABRAIN_REDIS_PORT=6379

# New configuration format
SOMABRAIN_REDIS_URL=redis://localhost:6379/0
```

#### API Changes
```python
# Old API (v0.0.x)
response = requests.post('/store', json={'text': 'content'})

# New API (v0.1.0)
response = requests.post('/remember', json={
    'content': 'content',
    'metadata': {'category': 'example'}
})
```

#### Docker Compose Updates
```bash
# Update docker-compose.yml to v0.1.0 format
curl -sSL https://raw.githubusercontent.com/somatechlat/somabrain/v0.1.0/docker-compose.yml -o docker-compose.yml

# Migrate data (if preserving existing memories)
./scripts/migrate-v0-to-v1.sh
```

---

## Release Process

### Semantic Versioning Policy
- **MAJOR** (x.0.0): Breaking API changes, major architectural changes
- **MINOR** (0.x.0): New features, backward-compatible improvements
- **PATCH** (0.0.x): Bug fixes, security patches, documentation updates

### Release Criteria
Before any release, these requirements must be met:
- [ ] All property tests pass validating mathematical invariants
- [ ] Integration tests pass in strict real mode
- [ ] Performance benchmarks meet or exceed previous version
- [ ] Security scan passes with no critical vulnerabilities
- [ ] Documentation updated for all changes
- [ ] Migration guide provided for breaking changes
- [ ] Changelog updated with all changes categorized

### Support Policy
- **Current Major Version**: Full support with bug fixes and security patches
- **Previous Major Version**: Security patches only for 12 months
- **Older Versions**: End of life, upgrade recommended

---

## Breaking Changes Policy

SomaBrain follows these principles for breaking changes:

### Major Version Changes (1.0.0 → 2.0.0)
- API endpoint changes or removal
- Configuration format changes
- Mathematical algorithm changes affecting results
- Database schema changes requiring migration

### Minor Version Changes (1.0.0 → 1.1.0)
- New optional API parameters
- New configuration options with sensible defaults
- Performance improvements without result changes
- New features that don't affect existing functionality

### Patch Version Changes (1.0.0 → 1.0.1)
- Bug fixes that don't change expected behavior
- Security vulnerability fixes
- Documentation corrections
- Performance optimizations without behavioral changes

### Deprecation Process
1. **Announce**: Feature marked as deprecated in changelog and documentation
2. **Warning Period**: Minimum 6 months with deprecation warnings in logs
3. **Removal**: Feature removed in next major version with migration guide

---

**Verification**: Check version compatibility and review breaking changes before upgrading.

**Common Errors**:
- Version mismatch → Verify client library and server versions are compatible
- Configuration errors → Review migration guide for configuration format changes
- API integration failures → Check API changelog for endpoint or parameter changes

**References**:
- [Semantic Versioning Specification](https://semver.org/) for versioning policy understanding
- [Migration Guides](#migration-guides) for upgrade procedures
- [API Documentation](development-manual/api-reference.md) for current API specification
