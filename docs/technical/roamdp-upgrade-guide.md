# ROAMDP Upgrade Guide - Complete Implementation

## **Overview**

This document captures the complete implementation of **ROAMDP Phase 3** across the entire SomaBrain codebase, including the hard cleanup of all legacy code patterns.

## **Implementation Summary**

### **Phase 1: Per-Tenant Circuit Breakers** ✅
- **Status**: COMPLETE
- **Architecture**: `AsyncCircuitBreaker` per tenant namespace
- **Metrics**: Prometheus gauges with tenant labels
- **Monitoring**: Health watchdog coroutine

### **Phase 2: Health Monitoring** ✅  
- **Status**: COMPLETE
- **Implementation**: `_health_watchdog_coroutine()` in app.py
- **Metrics**: Per-tenant health status
- **Failover**: Automatic circuit reset on health recovery

### **Phase 3: Memory Outbox & Write Modes** ✅
- **Status**: COMPLETE + HARD CLEANUP
- **Architecture**: HTTP-first with DB-backed outbox only
- **Persistence**: `enqueue_event()` transactional outbox
- **Isolation**: Per-tenant dedupe keys and topics

### **Phase 4: Legacy Code Purge** ✅
- **Status**: COMPLETE
- **Removed Components**:
  - File-based outbox system
  - Local/Redis backend modes
  - Legacy shared_settings fallbacks
  - Complex environment variable fallbacks
  - Deprecated initialization methods

## **Code Changes by Component**

### **MemoryClient (`somabrain/memory_client.py`)**

#### **Before ROAMDP**
```python
# Legacy patterns
- File-based _record_outbox()
- shared_settings fallbacks
- Local mode (_init_local())
- Redis mode (_init_redis())
- Complex environment fallbacks
- Legacy fast_ack configuration
```

#### **After ROAMDP**
```python
# Clean architecture
- HTTP-only with enqueue_event() DB outbox
- Direct environment configuration
- Tenant isolation via namespace extraction
- Clean HTTP client initialization
- No legacy fallbacks
```

#### **Specific Changes**
1. **Removed `_record_outbox()` file-based implementation**
2. **Added `enqueue_event()` DB outbox integration**
3. **Removed `_init_local()` and `_init_redis()` methods**
4. **Simplified `_init_http()` to core HTTP configuration**
5. **Removed `shared_settings` dependencies**
6. **Added `_tenant_id` namespace extraction**
7. **Added X-Soma-Tenant headers to all HTTP requests**
8. **Added X-Idempotency-Key headers**

### **Configuration (`somabrain/config.py`)**
- **Added**: `memory_write_mode` configuration
- **Added**: Per-tenant circuit breaker settings
- **Removed**: Legacy fallback patterns

### **Database Models**
- **Added**: `outbox_events` table via migration
- **Added**: `OutboxEvent` model with tenant_id column
- **Added**: Unique dedupe_key constraint

### **HTTP Integration**
- **Enhanced**: All HTTP methods include tenant headers
- **Added**: Idempotency key support
- **Enhanced**: Retry logic with tenant context

## **Environment Variables - Clean Set**

```bash
# Required
SOMABRAIN_MEMORY_HTTP_ENDPOINT=https://memory.service
SOMABRAIN_MEMORY_HTTP_TOKEN=your-token

# Optional tuning
SOMABRAIN_MEMORY_FAILURE_THRESHOLD=3
SOMABRAIN_MEMORY_RESET_INTERVAL=60
SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL=5.0

# Debug
SOMABRAIN_DEBUG_MEMORY_CLIENT=1
```

## **Tenant Architecture**

### **Namespace → Tenant Mapping**
```
"memory:sandbox-tenant" → tenant_id="sandbox-tenant"
"production:user123" → tenant_id="user123"
```

### **Isolation Guarantees**
- **Circuit breakers**: Per-tenant AsyncCircuitBreaker
- **Outbox records**: Per-tenant dedupe keys
- **Metrics**: Prometheus gauges with tenant labels
- **HTTP headers**: X-Soma-Tenant propagation

## **Database Schema Changes**

### **Outbox Events Table**
```sql
CREATE TABLE outbox_events (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    topic VARCHAR NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR DEFAULT 'pending',
    retries INTEGER DEFAULT 0,
    dedupe_key VARCHAR UNIQUE NOT NULL,
    tenant_id VARCHAR,
    last_error TEXT
);
```

## **API Headers Added**

### **All HTTP Requests Include:**
- `X-Soma-Tenant: {tenant_id}`
- `X-Idempotency-Key: {uuid4}` (derived from X-Request-ID)

## **Testing Status**

### **Test Coverage**
- ✅ `test_roamdp_phase3.py` - 6/6 tests passing
- ✅ Tenant extraction verification
- ✅ DB outbox functionality
- ✅ HTTP header injection
- ✅ Per-tenant isolation

### **Integration Tests**
- ✅ Health monitoring per tenant
- ✅ Circuit breaker state changes
- ✅ Outbox event enqueuing
- ✅ HTTP failure recovery

## **Migration Path**

### **Zero-Downtime Deployment**
1. **Phase 1**: Deploy per-tenant circuit breakers
2. **Phase 2**: Add health monitoring
3. **Phase 3**: Switch to DB outbox (HTTP-first)
4. **Phase 4**: Purge legacy code (this implementation)

### **Rollback Safety**
- **HTTP-first**: Always returns to HTTP service
- **DB outbox**: Preserves all writes during outages
- **Circuit breakers**: Graceful degradation

## **Performance Impact**

### **Improvements**
- **Tenant isolation**: Prevents cross-tenant failures
- **Circuit breakers**: Reduces cascading failures
- **DB outbox**: Reliable persistence during outages
- **Clean architecture**: Reduced complexity overhead

## **Monitoring**

### **Prometheus Metrics**
- `memory_circuit_open{tenant}` - Circuit breaker state
- `memory_outbox_pending{tenant}` - Pending outbox events
- `memory_write_latency{tenant}` - Write latency histograms

## **Deployment Checklist**

### **Infrastructure**
- [ ] Memory service endpoint configured
- [ ] Authentication token provided
- [ ] Postgres database with outbox_events table
- [ ] Kafka configured for outbox publishing

### **Configuration**
- [ ] Environment variables set
- [ ] Circuit breaker thresholds configured
- [ ] Health poll interval set
- [ ] Debug mode configured if needed

## **Final Status**

**✅ ROAMDP UPGRADE COMPLETE**
- All phases implemented
- All legacy code purged
- Production-ready configuration
- Zero-downtime migration path
- Comprehensive monitoring

**Ready for deployment with confidence.**