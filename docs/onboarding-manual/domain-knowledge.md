# Domain Knowledge

**Purpose**: Deep technical understanding of SomaBrain's cognitive memory platform, including mathematical foundations, architectural decisions, and business logic.

**Audience**: Developers who need comprehensive understanding of hyperdimensional computing, vector mathematics, and cognitive reasoning systems.

**Prerequisites**: Strong programming background, familiarity with [Codebase Walkthrough](codebase-walkthrough.md), and basic linear algebra knowledge.

---

## Cognitive Memory Fundamentals

### What is Cognitive Memory?

**Definition**: Cognitive memory systems store and retrieve information based on semantic meaning rather than exact matches, mimicking how human memory works.

**Key Characteristics**:
- **Associative**: Related concepts are stored and retrieved together
- **Fuzzy Matching**: Finds similar content even without exact keywords
- **Context Aware**: Considers metadata, timing, and relationships
- **Scalable**: Performance remains stable as memory grows
- **Persistent**: Maintains knowledge across sessions and updates

**Traditional vs. Cognitive Storage**:

| Traditional Database | Cognitive Memory |
|---------------------|------------------|
| Exact keyword matching | Semantic similarity |
| Structured queries | Natural language queries |
| Fixed schema | Flexible metadata |
| Boolean results | Scored relevance |
| Linear search complexity | Logarithmic search complexity |

### SomaBrain's Approach

**Hyperdimensional Computing (HDC)**:
- **Vector Representations**: Convert text to high-dimensional numerical vectors
- **Semantic Preservation**: Similar meanings → similar vectors
- **Mathematical Operations**: Use vector arithmetic for reasoning
- **Efficient Storage**: Optimized for similarity computations

**Mathematical Foundation**:
```python
# Vector similarity using cosine distance
def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Compute semantic similarity between two memory vectors.
    
    Returns value between -1 (opposite) and 1 (identical).
    Values > 0.7 typically indicate strong semantic relationship.
    """
    dot_product = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
    
    if norms == 0:
        return 0.0
    
    return dot_product / norms

# Memory storage process
def store_memory(content: str, metadata: dict) -> str:
    """
    Complete memory storage pipeline.
    
    1. Text preprocessing (cleaning, normalization)
    2. Vector encoding using transformer models
    3. Metadata enrichment and validation
    4. Database storage with indexing
    5. Cache population for fast retrieval
    """
    
    # 1. Preprocess content
    clean_content = preprocess_text(content)
    
    # 2. Encode to vector using sentence transformers
    vector = sentence_transformer.encode(clean_content)
    
    # 3. Enrich metadata with automatic tags
    enriched_metadata = enrich_metadata(metadata, clean_content)
    
    # 4. Store in PostgreSQL with pgvector
    memory_id = database.store_memory(
        content=clean_content,
        vector=vector,
        metadata=enriched_metadata,
        tenant_id=current_tenant
    )
    
    # 5. Update cache for fast access
    cache.store_memory_summary(memory_id, vector, enriched_metadata)
    
    return memory_id
```

---

## 🔬 Mathematical Foundations & Validation

| Invariant | Description | Enforcement |
| --- | --- | --- |
| Density matrix trace | `abs(trace(ρ) - 1) < 1e-4` | `somabrain/memory/density.py` renormalizes after each update. |
| PSD stability | Negative eigenvalues are clipped so ρ stays PSD | `DensityMatrix.project_psd()` trims the spectrum. |
| Scorer bounds | Component weights stay within configured bounds | `somabrain/scoring.py` clamps weights and exports metrics. |
| Strict-mode audit | Stub usage raises `RuntimeError` | `_audit_stub_usage` inside `somabrain/memory_client.py`. |
| Governance | Rate limits, OPA policy, neuromodulator feedback | Middleware stack inside `somabrain.app` and controls modules. |

All mathematical invariants are monitored through `/metrics` with Prometheus integration.

---

## Vector Encoding Architecture

### Transformer Models

**Current Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384 (balanced performance/accuracy)
- **Context Length**: 256 tokens (~200 words)
- **Training**: Optimized for semantic textual similarity
- **Performance**: ~50ms encoding time, ~95% accuracy on benchmarks

**Alternative Models**:

| Model | Dimensions | Speed | Accuracy | Use Case |
|-------|------------|-------|----------|----------|
| all-MiniLM-L6-v2 | 384 | Fast | High | Production default |
| all-mpnet-base-v2 | 768 | Medium | Very High | Quality-critical applications |
| distilbert-base-nli | 768 | Medium | High | Research and development |
| paraphrase-multilingual | 512 | Slow | High | Multi-language support |

### Vector Operations

**Encoding Pipeline**:
```python
class VectorEncoder:
    """
    High-performance text-to-vector encoding system.
    
    Features:
    - Batch processing for efficiency
    - GPU acceleration when available  
    - Automatic text preprocessing
    - Vector normalization for consistency
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize encoder with specified transformer model."""
        self.model = SentenceTransformer(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        
        # Enable mixed precision for speed
        if self.device == "cuda":
            self.model.half()
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode single text to normalized vector."""
        
        # Preprocess text
        clean_text = self.preprocess_text(text)
        
        # Handle empty text
        if not clean_text.strip():
            return np.zeros(self.model.get_sentence_embedding_dimension())
        
        # Encode with model
        vector = self.model.encode(
            clean_text,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization
        )
        
        return vector.astype(np.float32)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Efficiently encode multiple texts."""
        
        if not texts:
            return np.array([])
        
        # Preprocess all texts
        clean_texts = [self.preprocess_text(text) for text in texts]
        
        # Filter empty texts  
        valid_indices = [i for i, text in enumerate(clean_texts) if text.strip()]
        valid_texts = [clean_texts[i] for i in valid_indices]
        
        if not valid_texts:
            empty_vector = np.zeros(self.model.get_sentence_embedding_dimension())
            return np.array([empty_vector] * len(texts))
        
        # Batch encode
        vectors = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(valid_texts) > 100
        )
        
        # Reconstruct full result array
        result = np.zeros((len(texts), vectors.shape[1]), dtype=np.float32)
        for i, valid_idx in enumerate(valid_indices):
            result[valid_idx] = vectors[i]
        
        return result
    
    def preprocess_text(self, text: str) -> str:
        """Clean and normalize text for encoding."""
        
        # Basic cleaning
        text = text.strip()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Handle special characters and encoding
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        # Truncate to model limits (with some buffer)
        max_length = 200  # Leave room for tokenization overhead
        words = text.split()
        if len(words) > max_length:
            text = ' '.join(words[:max_length])
        
        return text
```

### Similarity Computation

**Distance Metrics**:
```python
def compute_similarities(query_vector: np.ndarray, memory_vectors: np.ndarray) -> np.ndarray:
    """
    Compute similarity scores between query and memory vectors.
    
    Uses cosine similarity for semantic relationship measurement.
    Optimized for large-scale vector operations.
    """
    
    # Ensure vectors are normalized
    query_norm = query_vector / np.linalg.norm(query_vector)
    memory_norms = memory_vectors / np.linalg.norm(memory_vectors, axis=1, keepdims=True)
    
    # Compute cosine similarities using matrix multiplication
    similarities = np.dot(memory_norms, query_norm)
    
    return similarities

def similarity_search(
    query_vector: np.ndarray,
    memory_vectors: np.ndarray,
    metadata: List[dict],
    k: int = 10,
    threshold: float = 0.2
) -> List[Tuple[int, float]]:
    """
    Find k most similar memories above threshold.
    
    Returns list of (memory_index, similarity_score) tuples.
    """
    
    # Compute all similarities
    similarities = compute_similarities(query_vector, memory_vectors)
    
    # Filter by threshold
    valid_indices = np.where(similarities >= threshold)[0]
    valid_similarities = similarities[valid_indices]
    
    # Sort by similarity (descending)
    sorted_indices = np.argsort(valid_similarities)[::-1]
    
    # Return top k results
    results = []
    for i in sorted_indices[:k]:
        memory_idx = valid_indices[i]
        similarity = valid_similarities[i]
        results.append((memory_idx, similarity))
    
    return results
```

---

## Database Architecture

### PostgreSQL with pgvector

**Schema Design**:
```sql
-- Main memory storage table
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    vector_encoding VECTOR(384) NOT NULL,  -- pgvector extension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT content_not_empty CHECK (length(trim(content)) > 0),
    CONSTRAINT vector_dimension_check CHECK (array_length(vector_encoding, 1) = 384)
);

-- Indexes for performance
CREATE INDEX CONCURRENTLY idx_memories_tenant_created 
    ON memories (tenant_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_memories_metadata_gin 
    ON memories USING GIN (metadata);

-- Vector similarity index (HNSW for approximate nearest neighbor)
CREATE INDEX CONCURRENTLY idx_memories_vector_hnsw 
    ON memories USING hnsw (vector_encoding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

-- Exact vector index for smaller datasets
CREATE INDEX CONCURRENTLY idx_memories_vector_ivfflat 
    ON memories USING ivfflat (vector_encoding vector_cosine_ops) 
    WITH (lists = 100);
```

**Query Optimization**:
```sql
-- Optimized similarity search query
EXPLAIN (ANALYZE, BUFFERS) 
SELECT 
    id,
    content,
    metadata,
    1 - (vector_encoding <=> $1::vector) as similarity_score
FROM memories 
WHERE 
    tenant_id = $2
    AND 1 - (vector_encoding <=> $1::vector) >= $3  -- Threshold filter
    AND metadata @> $4::jsonb  -- Metadata filter using GIN index
ORDER BY vector_encoding <=> $1::vector  -- pgvector distance operator
LIMIT $5;

-- Query plan analysis shows:
-- 1. Index scan on tenant_id (fast tenant isolation)
-- 2. Vector similarity using HNSW index (sub-linear search)
-- 3. GIN index for metadata filtering (efficient JSON queries)
-- 4. Minimal memory usage with streaming results
```

### Connection Pooling and Performance

**Connection Management**:
```python
class DatabasePool:
    """
    High-performance PostgreSQL connection pool.
    
    Features:
    - Async connections using asyncpg
    - Connection health monitoring
    - Query timeout handling
    - Prepared statement caching
    - Transaction management
    """
    
    def __init__(self, database_url: str, pool_size: int = 20):
        self.database_url = database_url
        self.pool_size = pool_size
        self.pool = None
        
    async def initialize(self):
        """Create connection pool with optimized settings."""
        
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,                    # Minimum connections
            max_size=self.pool_size,       # Maximum connections  
            max_queries=50000,             # Queries per connection
            max_inactive_connection_lifetime=300,  # 5 minute timeout
            command_timeout=30,            # Query timeout
            server_settings={
                'application_name': 'somabrain_api',
                'tcp_keepalives_idle': '600',
                'tcp_keepalives_interval': '30',
                'tcp_keepalives_count': '3'
            }
        )
        
        # Prepare common queries for performance
        async with self.pool.acquire() as conn:
            await self.prepare_statements(conn)
    
    async def prepare_statements(self, conn):
        """Prepare frequently-used queries for better performance."""
        
        # Memory storage query
        await conn.prepare("""
            INSERT INTO memories (tenant_id, content, metadata, vector_encoding)
            VALUES ($1, $2, $3, $4::vector)
            RETURNING id
        """)
        
        # Similarity search query
        await conn.prepare("""
            SELECT id, content, metadata, 
                   1 - (vector_encoding <=> $1::vector) as similarity_score
            FROM memories 
            WHERE tenant_id = $2 
              AND 1 - (vector_encoding <=> $1::vector) >= $3
            ORDER BY vector_encoding <=> $1::vector
            LIMIT $4
        """)
    
    async def execute_similarity_search(
        self,
        query_vector: np.ndarray,
        tenant_id: str,
        threshold: float,
        limit: int
    ) -> List[dict]:
        """Execute optimized similarity search."""
        
        async with self.pool.acquire() as conn:
            # Use prepared statement for performance
            rows = await conn.fetch(
                "similarity_search_query",
                query_vector.tolist(),  # Convert numpy to list for postgres
                tenant_id,
                threshold,
                limit
            )
            
            return [dict(row) for row in rows]
```

---

## Cognitive Reasoning System

### Reasoning Chain Architecture

**Multi-Step Reasoning**:
```python
class CognitiveReasoner:
    """
    Multi-step reasoning system that chains memory retrieval
    with logical inference to answer complex questions.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.reasoning_cache = LRUCache(maxsize=1000)
        
    async def generate_reasoning_chain(
        self,
        context: str,
        evidence_memories: List[Memory],
        reasoning_depth: str = "detailed"
    ) -> ReasoningChain:
        """
        Generate step-by-step reasoning from memories and context.
        
        Process:
        1. Extract key concepts from context
        2. Find supporting and contradicting evidence
        3. Build logical chain from premises to conclusion
        4. Assign confidence scores to each step
        5. Validate reasoning consistency
        """
        
        # Check cache first
        cache_key = self.hash_reasoning_input(context, evidence_memories)
        if cache_key in self.reasoning_cache:
            return self.reasoning_cache[cache_key]
        
        # Extract concepts and relationships
        concepts = await self.extract_concepts(context)
        relationships = await self.find_concept_relationships(concepts, evidence_memories)
        
        # Build reasoning steps
        reasoning_steps = []
        
        for concept in concepts:
            # Find supporting evidence
            supporting_memories = [
                m for m in evidence_memories 
                if self.supports_concept(m, concept)
            ]
            
            if supporting_memories:
                step = ReasoningStep(
                    step_number=len(reasoning_steps) + 1,
                    concept=concept,
                    premise=self.extract_premise(supporting_memories),
                    evidence=supporting_memories,
                    confidence=self.calculate_confidence(supporting_memories),
                    reasoning_type="evidence_based"
                )
                reasoning_steps.append(step)
        
        # Generate conclusion
        conclusion = await self.synthesize_conclusion(
            context, reasoning_steps, reasoning_depth
        )
        
        reasoning_chain = ReasoningChain(
            context=context,
            steps=reasoning_steps,
            conclusion=conclusion,
            overall_confidence=self.calculate_chain_confidence(reasoning_steps),
            evidence_count=len(evidence_memories)
        )
        
        # Cache result
        self.reasoning_cache[cache_key] = reasoning_chain
        
        return reasoning_chain
    
    def calculate_confidence(self, memories: List[Memory]) -> float:
        """
        Calculate confidence score based on memory quality and consistency.
        
        Factors:
        - Number of supporting memories (more = higher confidence)
        - Similarity scores (higher = more relevant)
        - Memory age (recent = more reliable)
        - Source credibility (from metadata)
        - Consistency between memories
        """
        
        if not memories:
            return 0.0
        
        # Base confidence from similarity scores
        similarity_scores = [m.similarity_score for m in memories if m.similarity_score]
        avg_similarity = np.mean(similarity_scores) if similarity_scores else 0.5
        
        # Boost for multiple supporting memories
        memory_count_factor = min(len(memories) / 5.0, 1.0)  # Max boost at 5 memories
        
        # Age factor (newer memories are more reliable)
        age_factor = self.calculate_age_factor(memories)
        
        # Source credibility factor
        credibility_factor = self.calculate_credibility_factor(memories)
        
        # Consistency factor (similar memories saying same thing)
        consistency_factor = self.calculate_consistency_factor(memories)
        
        # Combine factors (weighted average)
        confidence = (
            0.3 * avg_similarity +
            0.2 * memory_count_factor +
            0.2 * age_factor +
            0.15 * credibility_factor +
            0.15 * consistency_factor
        )
        
        return min(confidence, 0.99)  # Cap at 99% confidence
    
    async def synthesize_conclusion(
        self,
        context: str,
        steps: List[ReasoningStep],
        depth: str
    ) -> ReasoningConclusion:
        """
        Synthesize final conclusion from reasoning steps.
        
        Uses logical inference rules to combine premises
        into coherent conclusions with appropriate confidence.
        """
        
        if not steps:
            return ReasoningConclusion(
                conclusion="Insufficient evidence for reasoning",
                confidence=0.0,
                reasoning_type="insufficient_evidence"
            )
        
        # Group steps by confidence level
        high_confidence_steps = [s for s in steps if s.confidence >= 0.7]
        medium_confidence_steps = [s for s in steps if 0.4 <= s.confidence < 0.7]
        
        # Build conclusion based on strongest evidence
        if high_confidence_steps:
            conclusion_text = self.build_strong_conclusion(
                context, high_confidence_steps, depth
            )
            confidence = np.mean([s.confidence for s in high_confidence_steps])
        elif medium_confidence_steps:
            conclusion_text = self.build_tentative_conclusion(
                context, medium_confidence_steps, depth
            )
            confidence = np.mean([s.confidence for s in medium_confidence_steps]) * 0.8
        else:
            conclusion_text = "Evidence suggests possible connection, but confidence is low"
            confidence = 0.3
        
        return ReasoningConclusion(
            conclusion=conclusion_text,
            confidence=confidence,
            supporting_steps=[s.step_number for s in high_confidence_steps],
            reasoning_type="synthesized"
        )
```

### Pattern Recognition

**Memory Pattern Analysis**:
```python
class PatternAnalyzer:
    """
    Analyzes patterns and relationships in stored memories
    to discover implicit knowledge and connections.
    """
    
    async def analyze_topic_clusters(
        self,
        memories: List[Memory],
        max_clusters: int = 10
    ) -> List[TopicCluster]:
        """
        Discover topic clusters using vector similarity and metadata.
        
        Uses hierarchical clustering on vector embeddings
        combined with metadata analysis for semantic grouping.
        """
        
        if len(memories) < 2:
            return []
        
        # Extract vectors and metadata
        vectors = np.array([m.vector_encoding for m in memories])
        metadata_features = self.extract_metadata_features(memories)
        
        # Combine vector and metadata features
        combined_features = np.hstack([vectors, metadata_features])
        
        # Perform clustering
        from sklearn.cluster import AgglomerativeClustering
        
        n_clusters = min(max_clusters, len(memories) // 3)  # At least 3 memories per cluster
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage='ward'
        )
        
        cluster_labels = clustering.fit_predict(combined_features)
        
        # Build cluster objects
        clusters = []
        for cluster_id in range(n_clusters):
            cluster_memories = [
                memories[i] for i, label in enumerate(cluster_labels) 
                if label == cluster_id
            ]
            
            if len(cluster_memories) >= 2:  # Only meaningful clusters
                cluster = await self.build_topic_cluster(cluster_id, cluster_memories)
                clusters.append(cluster)
        
        return sorted(clusters, key=lambda c: c.coherence_score, reverse=True)
    
    async def detect_temporal_patterns(
        self,
        memories: List[Memory],
        time_window_days: int = 30
    ) -> List[TemporalPattern]:
        """
        Detect patterns in memory creation over time.
        
        Identifies:
        - Topic trends (increasing/decreasing interest)
        - Periodic patterns (weekly/monthly cycles)  
        - Burst events (sudden activity spikes)
        - Knowledge evolution (concept development over time)
        """
        
        # Group memories by time windows
        time_groups = defaultdict(list)
        
        for memory in memories:
            # Convert to time window bucket
            bucket = self.get_time_bucket(memory.created_at, time_window_days)
            time_groups[bucket].append(memory)
        
        patterns = []
        
        # Analyze each time window
        for bucket, bucket_memories in time_groups.items():
            if len(bucket_memories) < 3:  # Need minimum for pattern detection
                continue
            
            # Extract topics and concepts
            topics = await self.extract_topics(bucket_memories)
            
            # Compare with previous time windows
            previous_bucket = bucket - timedelta(days=time_window_days)
            if previous_bucket in time_groups:
                previous_topics = await self.extract_topics(time_groups[previous_bucket])
                
                # Detect trends
                trend = self.analyze_topic_trend(topics, previous_topics)
                if trend.significance > 0.5:
                    pattern = TemporalPattern(
                        pattern_type="trend",
                        time_period=bucket,
                        description=trend.description,
                        confidence=trend.significance,
                        affected_memories=bucket_memories
                    )
                    patterns.append(pattern)
        
        return patterns
```

---

## Business Logic

### Multi-Tenancy Architecture

**Tenant Isolation**:
```python
class TenantManager:
    """
    Manages tenant isolation, quotas, and security policies.
    
    Ensures complete data isolation between tenants while
    maintaining performance and operational efficiency.
    """
    
    def __init__(self, database: DatabaseManager, cache: CacheManager):
        self.database = database
        self.cache = cache
        self.tenant_configs = {}
    
    async def validate_tenant_access(
        self,
        tenant_id: str,
        api_key: str,
        operation: str
    ) -> TenantContext:
        """
        Validate tenant access and return context with limits.
        
        Checks:
        - API key validity and permissions
        - Tenant exists and is active
        - Operation is allowed for tenant tier
        - Rate limits and quotas
        """
        
        # Check cache first
        cache_key = f"tenant_access:{tenant_id}:{api_key}"
        cached_context = await self.cache.get(cache_key)
        
        if cached_context and not self.is_cache_expired(cached_context):
            return cached_context
        
        # Validate API key
        tenant_config = await self.database.get_tenant_config(tenant_id)
        if not tenant_config:
            raise AuthenticationError(f"Tenant {tenant_id} not found")
        
        if not self.verify_api_key(api_key, tenant_config.api_key_hash):
            raise AuthenticationError("Invalid API key")
        
        # Check tenant status
        if tenant_config.status != "active":
            raise AuthorizationError(f"Tenant {tenant_id} is {tenant_config.status}")
        
        # Check operation permissions
        if not self.check_operation_permission(operation, tenant_config.tier):
            raise AuthorizationError(f"Operation {operation} not allowed for tier {tenant_config.tier}")
        
        # Create context with current usage
        current_usage = await self.get_current_usage(tenant_id)
        
        context = TenantContext(
            tenant_id=tenant_id,
            tier=tenant_config.tier,
            limits=tenant_config.limits,
            current_usage=current_usage,
            permissions=tenant_config.permissions
        )
        
        # Cache context
        await self.cache.set(cache_key, context, ttl=300)  # 5 minute cache
        
        return context
    
    async def enforce_rate_limits(
        self,
        tenant_id: str,
        operation: str,
        context: TenantContext
    ) -> bool:
        """
        Enforce rate limiting based on tenant tier and current usage.
        
        Uses sliding window rate limiting with Redis for
        accurate distributed rate limiting.
        """
        
        limit_key = f"rate_limit:{tenant_id}:{operation}"
        window_seconds = 60  # 1 minute window
        
        # Get operation-specific limits
        operation_limits = context.limits.get(operation, {})
        requests_per_minute = operation_limits.get('requests_per_minute', 100)
        
        # Sliding window rate limiting using Redis
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Remove expired entries
        await self.cache.redis.zremrangebyscore(limit_key, 0, window_start)
        
        # Count current requests in window
        current_count = await self.cache.redis.zcard(limit_key)
        
        if current_count >= requests_per_minute:
            # Rate limit exceeded
            retry_after = await self.calculate_retry_after(limit_key, window_seconds)
            raise RateLimitError(
                f"Rate limit exceeded: {current_count}/{requests_per_minute} per minute",
                retry_after=retry_after
            )
        
        # Add current request to window
        await self.cache.redis.zadd(limit_key, {str(current_time): current_time})
        await self.cache.redis.expire(limit_key, window_seconds + 10)  # Cleanup buffer
        
        return True
    
    async def check_storage_quota(
        self,
        tenant_id: str,
        additional_content_size: int,
        context: TenantContext
    ) -> bool:
        """Check if tenant can store additional content within quota."""
        
        storage_limit = context.limits.get('max_storage_mb', 1000)  # Default 1GB
        current_storage = context.current_usage.get('storage_mb', 0)
        
        additional_mb = additional_content_size / (1024 * 1024)
        
        if current_storage + additional_mb > storage_limit:
            raise QuotaExceededError(
                f"Storage quota exceeded: {current_storage + additional_mb:.2f}MB / {storage_limit}MB"
            )
        
        return True
```

### Security and Compliance

**Data Security**:
```python
class SecurityManager:
    """
    Manages data security, encryption, and compliance requirements.
    
    Features:
    - Content encryption at rest and in transit
    - PII detection and redaction
    - Audit logging for compliance
    - Access control and permissions
    """
    
    def __init__(self, encryption_key: str, audit_logger: AuditLogger):
        self.cipher = Fernet(encryption_key.encode())
        self.audit_logger = audit_logger
        self.pii_detector = PIIDetector()
    
    async def secure_content_storage(
        self,
        content: str,
        metadata: dict,
        tenant_id: str,
        user_id: str
    ) -> SecureContent:
        """
        Secure content before storage with encryption and PII handling.
        
        Process:
        1. Detect and handle PII in content
        2. Encrypt sensitive data fields
        3. Generate audit trail
        4. Return secured content for storage
        """
        
        # Detect PII in content
        pii_findings = await self.pii_detector.scan_content(content)
        
        # Handle PII based on tenant policy
        processed_content, redaction_map = await self.handle_pii(
            content, pii_findings, tenant_id
        )
        
        # Encrypt sensitive metadata fields
        secure_metadata = await self.encrypt_sensitive_metadata(metadata)
        
        # Generate audit log entry
        audit_entry = AuditEntry(
            tenant_id=tenant_id,
            user_id=user_id,
            action="content_storage",
            content_hash=self.hash_content(processed_content),
            pii_detected=len(pii_findings) > 0,
            encryption_applied=True,
            timestamp=datetime.utcnow()
        )
        
        await self.audit_logger.log_entry(audit_entry)
        
        return SecureContent(
            content=processed_content,
            metadata=secure_metadata,
            redaction_map=redaction_map,
            audit_id=audit_entry.id
        )
    
    async def handle_pii(
        self,
        content: str,
        pii_findings: List[PIIFinding],
        tenant_id: str
    ) -> Tuple[str, dict]:
        """
        Handle PII based on tenant data policy.
        
        Options:
        - Redact: Replace with placeholder tokens
        - Encrypt: Encrypt in place with tenant key
        - Remove: Delete PII sections entirely
        - Preserve: Keep with additional audit logging
        """
        
        tenant_policy = await self.get_tenant_pii_policy(tenant_id)
        redaction_map = {}
        processed_content = content
        
        for finding in sorted(pii_findings, key=lambda f: f.start, reverse=True):
            # Process from end to start to preserve indices
            pii_text = content[finding.start:finding.end]
            
            if tenant_policy.pii_handling == "redact":
                replacement = f"[{finding.pii_type.upper()}_REDACTED]"
                processed_content = (
                    processed_content[:finding.start] + 
                    replacement + 
                    processed_content[finding.end:]
                )
                redaction_map[finding.id] = {
                    "original_text": self.cipher.encrypt(pii_text.encode()).decode(),
                    "replacement": replacement,
                    "pii_type": finding.pii_type
                }
            
            elif tenant_policy.pii_handling == "encrypt":
                encrypted_text = self.cipher.encrypt(pii_text.encode()).decode()
                processed_content = (
                    processed_content[:finding.start] + 
                    f"[ENCRYPTED:{encrypted_text}]" + 
                    processed_content[finding.end:]
                )
            
            elif tenant_policy.pii_handling == "remove":
                processed_content = (
                    processed_content[:finding.start] + 
                    processed_content[finding.end:]
                )
                redaction_map[finding.id] = {
                    "removed_text": self.cipher.encrypt(pii_text.encode()).decode(),
                    "pii_type": finding.pii_type
                }
        
        return processed_content, redaction_map
```

## Learning Algorithm Diagnostics

SomaBrain's current adaptation engine lives in `somabrain/learning/adaptation.py`. Two internal analyses documented the same core flaw: **parameter coupling that creates the illusion of learning**. Preserve these findings while implementing fixes.

### Coupled Parameter Updates

```python
def apply_feedback(self, utility: float, reward: Optional[float] = None) -> bool:
    signal = reward if reward is not None else utility

    # Learning rate manipulation
    self._lr = self._base_lr * (1.0 + float(signal))
    delta = self._lr * float(signal)

    # Identical deltas across parameters
    self._retrieval.alpha = self._constrain("alpha", self._retrieval.alpha + delta)
    self._retrieval.gamma = self._constrain("gamma", self._retrieval.gamma - 0.5 * delta)
    self._utility.lambda_ = self._constrain("lambda_", self._utility.lambda_ + delta)
    self._utility.mu = self._constrain("mu", self._utility.mu - 0.25 * delta)
    self._utility.nu = self._constrain("nu", self._utility.nu - 0.25 * delta)
    return True
```

- `alpha` and `lambda_` move together because they share the same `+delta` updates.
- `gamma` starts at 0.1 and the `-0.5 * delta` term drives it to the floor (`0.0`) quickly.
- Learning rate becomes effectively constant for repeated positive feedback (`0.05 * (1.0 + 0.9) = 0.095`).

### Evidence from Telemetry and Tests

| Observation | Source |
| --- | --- |
| Linear growth for `alpha`/`lambda_` (`[1.0, 1.045, 1.09, …]`) | `run_learning_test.py` output |
| `gamma` hits 0.0 and remains clamped | Redis persistence of adaptation state |
| Tests expect `alpha` and `lambda_` to increase together | `tests/test_learning_progress.py` |
| State snapshot shows constant learning rate `0.095` | `somabrain/learning/adaptation.py` telemetry |

### Diagnosis Summary

- The engine simulates learning by deterministic coupling rather than independent cognitive signals.
- Strict mode ensures no stubs hide the behaviour—failures are observable in Redis state and audit logs.
- Infrastructure (Redis, Kafka, metrics) is production ready; only the algorithm needs redesign.

### Recommended Fix Strategy

1. **Decouple parameters**: introduce independent deltas per signal (semantic quality, utility improvement, temporal relevance).
2. **Dynamic learning rates**: derive `alpha_lr`, `lambda_lr`, `gamma_lr` from neuromodulator state instead of a single `_base_lr` multiplier.
3. **True cognitive signals**: feed semantic relevance, cost/benefit ratios, and temporal freshness into the adaptation step.
4. **Guardrails**: add property tests verifying parameters diverge when signals differ; export dedicated metrics to confirm.

### Migration Checklist

- [ ] Refactor `apply_feedback` with independent learning channels.
- [ ] Update tests to assert decorrelated parameter movement.
- [ ] Extend metrics (`somabrain_learning_alpha_delta`, etc.) for visibility.
- [ ] Document the new behaviour in this manual and update benchmarks.

## Mathematical Appendices

### Density Matrix Maintenance

`somabrain/memory/density.py` maintains the ρ matrix used by the unified scorer. Keep code and math synchronized.

- Representation: ρ is a real symmetric matrix with shape `(dim, dim)`.
- Updates: `DensityMatrix.observe(vec, alpha)` normalizes `vec`, applies the rank-1 update `ρ' = (1 - alpha) * ρ + alpha * (v vᵀ)`, then reprojects.
- Projection steps:
    1. Trace normalization via `normalize_trace()` so `trace(ρ) = 1`.
    2. PSD projection via `project_psd()` to clip negative eigenvalues.
    3. Symmetrization with `(ρ + ρᵀ) / 2` to counter floating point drift.
- Metrics: `somabrain_density_trace_error_total`, `somabrain_density_psd_clip_total`, `somabrain_density_condition_number`.
- Tests: `tests/test_fd_salience.py`, `tests/test_unified_scorer.py`, and `tests/test_legacy_purge.py` guard PSD, weight bounds, and stub regressions.

### BHDC Binding Cheat Sheet

`somabrain/quantum.py` implements binary hyperdimensional computing (BHDC). Key reminders:

- Hypervector construction: dimension from `HRRConfig.dim` (default 2048); RNG seeded with `HRRConfig.seed`; sparsity controls ones vs minus ones.
- Role generation: `QuantumLayer.make_unitary_role(role)` hashes the role, seeds a temporary RNG, and produces a permutation vector that is its own inverse.
- Binding & unbinding: `bind_unitary(vec, role)` performs circular convolution; `unbind_unitary(bound, role)` applies the conjugate to reverse the operation.
- Superposition & cleanup: `superpose` averages bound vectors and renormalizes to ±1; `cleanup` selects the stored vector with maximum cosine similarity.
- Tests: `tests/test_bhdc_binding.py` checks bind/unbind symmetry; `benchmarks/numerics_bench.py` validates numerical stability.

**Verification**: Domain knowledge is comprehensive when you understand the mathematical foundations, can explain architectural decisions, and can implement new cognitive features.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| Vector dimension mismatch | Ensure consistent model usage across encoding/storage |
| Poor similarity results | Check text preprocessing and vector normalization |
| Slow database queries | Optimize indexes and query structure |
| Memory usage spikes | Implement batch processing and connection pooling |
| Tenant data leakage | Verify all queries include tenant_id filtering |

**References**:
- [Codebase Walkthrough](codebase-walkthrough.md) for implementation details
- [First Contribution](first-contribution.md) for hands-on practice
- [Technical Manual](../technical-manual/index.md) for operational knowledge
- [API Reference](../development-manual/api-reference.md) for integration patterns