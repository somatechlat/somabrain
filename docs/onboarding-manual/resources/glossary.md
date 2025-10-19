# Project Glossary

**Purpose**: Comprehensive definition of technical terms, concepts, and domain-specific vocabulary used throughout SomaBrain.

**Audience**: All team members, contributors, and stakeholders needing clarification on terminology.

**Prerequisites**: Basic understanding of software development and cognitive computing concepts.

---

## Core Concepts

### Cognitive Memory
**Definition**: A memory system that mimics human-like associative recall, storing information with semantic understanding rather than exact matching.

**Usage**: "SomaBrain provides cognitive memory capabilities that allow AI agents to store and recall experiences contextually."

**Related Terms**: Semantic Memory, Episodic Memory, Associative Recall

### Hyperdimensional Computing (HDC)
**Definition**: A mathematical framework using very high-dimensional vectors (typically 1000+ dimensions) to represent and manipulate information, inspired by neural computation patterns.

**Usage**: "SomaBrain's hyperdimensional computing approach enables efficient similarity operations on high-dimensional semantic representations."

**Related Terms**: BHDC, Hypervector, Vector Symbolic Architecture

### Binary Hyperdimensional Computing (BHDC)
**Definition**: A specific form of HDC using binary vectors (elements are +1 or -1) with optimized binding and unbinding operations.

**Usage**: "BHDC binding allows SomaBrain to create compositional representations where concepts can be combined and later separated."

**Related Terms**: Binding, Unbinding, Hypervector

---

## Memory Architecture

### Working Memory
**Definition**: Fast, temporary memory cache storing recently accessed or frequently used memories for quick retrieval.

**Usage**: "The working memory system maintains active memories in Redis for sub-second access times."

**Technical Details**: Implemented in `somabrain/mt_wm.py` with configurable size limits and eviction policies.

### Long-term Memory
**Definition**: Persistent memory storage system for long-term retention of memories with full semantic encoding.

**Usage**: "Long-term memory provides durable storage for agent experiences and learned knowledge."

**Technical Details**: Backed by HTTP memory service with vector storage and retrieval capabilities.

### Memory Operations
**Definition**: The two primary functions for interacting with cognitive memory: storing (remember) and retrieving (recall).

- **Remember**: Store new information with semantic encoding and metadata
- **Recall**: Retrieve relevant memories based on semantic similarity to a query

**Usage**: "Memory operations are exposed via REST API endpoints `/remember` and `/recall`."

### Density Matrix (ρ)
**Definition**: Mathematical structure tracking relationships between stored memories, used for second-order recall and memory organization.

**Usage**: "The density matrix maintains memory relationships and enables contextual recall beyond simple similarity matching."

**Technical Details**: Must remain positive semi-definite (PSD) with trace normalization, implemented in `somabrain/memory/density.py`.

---

## Mathematical Operations

### Binding
**Definition**: Mathematical operation combining two hypervectors to create a composite representation, typically using element-wise multiplication for BHDC.

**Usage**: "BHDC binding allows encoding of relationships like 'Paris is-capital-of France' as bound hypervectors."

**Formula**: `c = a ⊛ b` where ⊛ represents the binding operation

### Unbinding
**Definition**: Inverse of binding operation, used to extract one component when given the bound result and the other component.

**Usage**: "Unbinding allows retrieval of 'France' when given the bound representation and the query 'capital'."

**Formula**: `a ≈ c ⊛ b` (approximate recovery due to noise)

### Salience
**Definition**: Measure of importance or relevance of a memory, used to prioritize recall and determine storage decisions.

**Usage**: "High salience memories are more likely to be recalled and retained in working memory."

**Technical Details**: Computed using novelty, error, and frequency-directions components.

### Frequent Directions (FD)
**Definition**: Sketching algorithm for maintaining approximate principal components of a data stream, used in SomaBrain for diversity-aware recall.

**Usage**: "FD salience ensures recalled memories are diverse rather than just similar to the query."

**Technical Details**: Implemented in `somabrain/salience.py` with configurable rank and decay parameters.

---

## System Architecture

### Multi-tenant Architecture
**Definition**: System design supporting multiple isolated users or applications sharing the same infrastructure while maintaining data separation.

**Usage**: "SomaBrain's multi-tenant design allows hosting multiple AI agents with complete memory isolation."

**Technical Details**: Implemented through namespace-based isolation in working memory and metadata tagging.

### Strict Real Mode
**Definition**: Production configuration that enforces use of real services and disables all stub/mock implementations.

**Usage**: "Backend enforcement (`SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1`) ensures production code paths are identical to development testing."

**Technical Details**: Runtime validation prevents stub usage and requires real Redis, PostgreSQL, and other backing services.

### Circuit Breaker Pattern
**Definition**: Resilience pattern that prevents cascading failures by temporarily disabling calls to a failing service.

**Usage**: "Circuit breakers protect SomaBrain from memory service outages by failing fast and allowing graceful degradation."

**States**: Closed (normal), Open (failing), Half-Open (testing recovery)

### Audit Trail
**Definition**: Immutable record of all operations and system events for security, compliance, and debugging purposes.

**Usage**: "The audit trail captures all memory operations with timestamps, user context, and operation metadata."

**Technical Details**: Structured JSON logs with optional Kafka publishing for real-time analysis.

---

## API & Integration

### REST API
**Definition**: Representational State Transfer API providing HTTP endpoints for all SomaBrain functionality.

**Usage**: "The REST API exposes memory operations through standard HTTP verbs and JSON payloads."

**Key Endpoints**: `/remember`, `/recall`, `/health`, `/metrics`

### Health Check
**Definition**: Endpoint that validates the operational status of SomaBrain and all its dependencies.

**Usage**: "Load balancers use the health check endpoint to determine service readiness."

**Response Codes**: 200 (healthy), 503 (degraded), 500 (unhealthy)

### Metrics Endpoint
**Definition**: Prometheus-compatible endpoint exposing operational and performance metrics.

**Usage**: "Monitoring systems scrape the metrics endpoint for observability data."

**Metrics Types**: Counters, gauges, histograms for various system behaviors

### JWT Authentication
**Definition**: JSON Web Token-based authentication system for securing API access.

**Usage**: "JWT tokens provide stateless authentication with configurable expiration and issuer validation."

**Format**: Standard JWT with claims for user identity, tenant, and permissions

---

## Development & Operations

### Property Testing
**Definition**: Testing methodology that validates system properties across randomly generated inputs rather than specific test cases.

**Usage**: "Property tests ensure mathematical invariants hold for all possible BHDC operations."

**Tools**: Hypothesis library for Python with custom strategies for hypervectors

### Mathematical Invariants
**Definition**: Properties that must always hold true in the system, used to validate correctness of algorithms.

**Examples**:
- Density matrix trace equals 1 (±1e-4)
- Positive semi-definite spectrum
- BHDC binding/unbinding roundtrip accuracy

### Container Orchestration
**Definition**: Automated deployment, scaling, and management of containerized applications.

**Usage**: "Docker Compose provides container orchestration for local development environments."

**Production**: Kubernetes with Helm charts for production deployments

### Observability
**Definition**: System's ability to be monitored, debugged, and understood through external outputs like logs, metrics, and traces.

**Components**: Logging (structured JSON), Metrics (Prometheus), Tracing (optional)

**Usage**: "Comprehensive observability enables rapid diagnosis and resolution of production issues."

---

## Business & Domain

### Agent-Coder
**Definition**: AI-powered software developer that can write, modify, and maintain code autonomously.

**Usage**: "SomaBrain's onboarding manual is specifically designed for agent-coders joining the development team."

**Capabilities**: Code generation, debugging, documentation, testing

### Memory-as-a-Service (MaaS)
**Definition**: Cloud service model providing cognitive memory capabilities through API interfaces.

**Usage**: "SomaBrain delivers memory-as-a-service to AI applications requiring persistent, semantic memory."

**Business Model**: Usage-based pricing with tenant isolation and SLA guarantees

### Semantic Similarity
**Definition**: Mathematical measure of meaning similarity between concepts, typically computed using vector similarity metrics.

**Usage**: "Semantic similarity drives memory recall by finding conceptually related memories rather than exact keyword matches."

**Computation**: Cosine similarity between hyperdimensional representations

### Knowledge Graph
**Definition**: Structured representation of knowledge as entities and relationships, used in SomaBrain for memory organization.

**Usage**: "Memory relationships form an implicit knowledge graph that enables reasoning and inference."

**Implementation**: Graph structure maintained through density matrix and explicit relationship links

---

## Acronyms & Abbreviations

| Acronym | Full Term | Context |
|---------|-----------|---------|
| **API** | Application Programming Interface | Web service interface |
| **BHDC** | Binary Hyperdimensional Computing | Core mathematical framework |
| **CI/CD** | Continuous Integration/Continuous Deployment | Development pipeline |
| **CPU** | Central Processing Unit | Hardware resource |
| **DNS** | Domain Name System | Network infrastructure |
| **FD** | Frequent Directions | Salience algorithm |
| **HDC** | Hyperdimensional Computing | Mathematical framework |
| **HTTP** | HyperText Transfer Protocol | Web communication |
| **JWT** | JSON Web Token | Authentication mechanism |
| **K8s** | Kubernetes | Container orchestration (8 chars between K and s) |
| **LTM** | Long-Term Memory | Memory architecture component |
| **MaaS** | Memory-as-a-Service | Business model |
| **OPA** | Open Policy Agent | Authorization engine |
| **PSD** | Positive Semi-Definite | Matrix property |
| **RAM** | Random Access Memory | Hardware resource |
| **REST** | Representational State Transfer | API architecture |
| **RTO** | Recovery Time Objective | Disaster recovery metric |
| **RPO** | Recovery Point Objective | Disaster recovery metric |
| **SLA** | Service Level Agreement | Business commitment |
| **SLO** | Service Level Objective | Performance target |
| **SRE** | Site Reliability Engineering | Operations discipline |
| **TLS** | Transport Layer Security | Network encryption |
| **WM** | Working Memory | Memory architecture component |

---

## Common Phrases & Expressions

### "No mocking, no mimicking, no fake data"
**Meaning**: Core principle emphasizing use of real mathematical operations and production-grade code paths.

**Context**: Used to reject shortcuts that compromise mathematical correctness or production readiness.

### "Strict real mode"
**Meaning**: Configuration requiring real services and disabling all stub implementations.

**Context**: Production deployment and testing philosophy ensuring environment parity.

### "Mathematical truth"
**Meaning**: Commitment to mathematically sound algorithms without approximations that compromise correctness.

**Context**: Algorithm design and validation approach.

### "Cognitive memory operations"
**Meaning**: Memory functions that understand semantic meaning rather than performing exact matching.

**Context**: Describing SomaBrain's core value proposition vs. traditional databases.

---

## Version-Specific Terms

### Legacy Terms (Deprecated)
| Term | Replacement | Deprecation |
|------|-------------|-------------|
| "Memory store" | "Long-term memory" | v0.1.0 |
| "Vector search" | "Semantic recall" | v0.1.0 |
| "AI memory" | "Cognitive memory" | v0.1.0 |

### Future Terms (Planned)
| Term | Definition | Target Version |
|------|------------|----------------|
| "Consolidation" | Background memory optimization process | v0.2.0 |
| "Metacognition" | Self-aware memory management | v0.3.0 |
| "Temporal reasoning" | Time-aware memory operations | v0.3.0 |

---

**Verification**: Team members can define key terms and use them consistently in documentation and code.

**Common Errors**:
- Mixing deprecated terms → Use current terminology from this glossary
- Inconsistent capitalization → Follow specific formatting rules (e.g., "SomaBrain" not "somabrain")
- Overloading terms → Use precise definitions rather than generic meanings

**References**:
- [Style Guide](../style-guide.md) for terminology usage rules
- [Technical Documentation](../../technical-manual/) for implementation details
- [API Reference](../../development-manual/api-reference.md) for endpoint-specific terms
- [Domain Knowledge](../domain-knowledge.md) for deep technical explanations
