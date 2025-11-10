# Guía del Agente de Propagación

**Propósito**: Comprender las operaciones de almacenamiento y recuperación de memoria en SomaBrain.

## Operaciones de Memoria (Verificadas en Código)

### 1. Remember (Almacenar Memoria)

**Endpoint**: `POST /remember`

**Implementación**: `somabrain/app.py` línea ~2800

**Cuerpo de Solicitud** (dos formatos soportados):

```json
{
  "payload": {
    "task": "París es la capital de Francia",
    "memory_type": "episodic",
    "timestamp": 1234567890
  }
}
```

O (formato legacy):

```json
{
  "task": "París es la capital de Francia",
  "memory_type": "episodic"
}
```

**Qué Sucede** (flujo de código real):

1. **Verificación Auth**: `require_auth(request, cfg)` - valida token Bearer
2. **Resolución Tenant**: `get_tenant(request, cfg.namespace)` - extrae ID de tenant
3. **Límite de Tasa**: `rate_limiter.allow(ctx.tenant_id)` - verifica límites RPS
4. **Verificación Cuota**: `quotas.allow_write(ctx.tenant_id, 1)` - límite diario de escritura
5. **Embedding**: `embedder.embed(text)` - genera vector
6. **Servicio Memoria**: `memsvc.aremember(key, payload)` - almacena en backend
7. **Admisión WM**: `mt_wm.admit(ctx.tenant_id, wm_vec, payload)` - agrega a memoria de trabajo
8. **Contexto HRR**: `mt_ctx.admit(ctx.tenant_id, anchor_id, hrr_vec)` - si HRR habilitado

**Respuesta**:

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns",
  "trace_id": "...",
  "deadline_ms": null,
  "idempotency_key": null
}
```

### 2. Recall (Recuperar Memoria)

**Endpoint**: `POST /recall`

**Implementación**: `somabrain/app.py` línea ~2400

**Solicitud**:

```json
{
  "query": "capital de Francia",
  "top_k": 3
}
```

**Qué Sucede** (flujo de código real):

1. **Embedding**: `embedder.embed(text)` - vector de consulta
2. **Recall WM**: `mt_wm.recall(ctx.tenant_id, wm_qv, top_k)` - hits de memoria de trabajo
3. **Recall LTM**: `_recall_ltm(mem_client, text, top_k, ...)` - memoria a largo plazo
4. **Puntuación**: `_score_memory_candidate(...)` - puntuación compuesta (coseno + FD + recencia)
5. **Cleanup HRR**: `mt_ctx.cleanup(ctx.tenant_id, hrr_qv)` - si habilitado
6. **Caché**: Resultados cacheados en `_recall_cache` con TTL de 2s

**Respuesta**:

```json
{
  "wm": [
    {"score": 0.95, "payload": {"task": "..."}}
  ],
  "memory": [
    {"task": "París es la capital de Francia", "timestamp": 1234567890}
  ],
  "results": [...],
  "namespace": "somabrain_ns",
  "trace_id": "..."
}
```

## Sistema de Puntuación (UnifiedScorer)

**Archivo**: `somabrain/scoring.py`

**Componentes** (pesos reales del código):

```python
w_cosine: float = 0.6      # Peso similitud coseno
w_fd: float = 0.25          # Peso Frequent-Directions
w_recency: float = 0.15     # Peso boost recencia
recency_tau: float = 32.0   # Constante de tiempo de decaimiento
```

**Fórmula**:

```
score = w_cosine * cosine(q, c) + w_fd * fd_sim(q, c) + w_recency * exp(-age/tau)
```

## Memoria de Trabajo (MultiTenantWM)

**Archivo**: `somabrain/mt_wm.py`

**Capacidad Predeterminada**: 64 elementos por tenant (`wm_size` en config)

**Operaciones**:
- `admit(tenant_id, vec, payload)` - agregar elemento
- `recall(tenant_id, query_vec, top_k)` - recuperar elementos similares
- `items(tenant_id)` - listar todos los elementos

## Contexto HRR (MultiTenantHRRContext)

**Archivo**: `somabrain/mt_context.py`

**Propósito**: Cleanup/desambiguación usando anclas hiperdimensionales

**Config** (de `HRRContextConfig`):
- `max_anchors`: 10000 (predeterminado)
- `decay_lambda`: 0.0 (sin decaimiento por defecto)
- `min_confidence`: 0.0 (aceptar todas las coincidencias)

**Operaciones**:
- `admit(tenant_id, anchor_id, hrr_vec)` - registrar ancla
- `cleanup(tenant_id, query_hrr)` - encontrar mejor ancla coincidente
- `analyze(tenant_id, hrr_vec)` - obtener puntuación + margen

## Cliente de Servicio de Memoria

**Archivo**: `somabrain/services/memory_service.py`

**Backend**: Servicio de memoria externo basado en HTTP

**Config Requerida**:
```python
http.endpoint = "http://localhost:9595"  # SOMABRAIN_MEMORY_HTTP_ENDPOINT
http.token = "devtoken"                   # SOMABRAIN_MEMORY_HTTP_TOKEN
```

**Circuit Breaker** (fail-fast):
- `_failure_threshold`: 3 fallos consecutivos
- `_reset_interval`: 60 segundos
- Lanza `RuntimeError` cuando circuito abierto

## Ejemplo: Flujo Completo de Remember

```python
# 1. Cliente envía solicitud
POST /remember
{
  "payload": {
    "task": "Aprender Python",
    "memory_type": "episodic"
  }
}

# 2. API procesa (somabrain/app.py)
# - Auth: require_auth()
# - Tenant: get_tenant() → "sandbox"
# - Límite tasa: rate_limiter.allow("sandbox") → True
# - Cuota: quotas.allow_write("sandbox", 1) → True
# - Embed: embedder.embed("Aprender Python") → [vector 256-dim]
# - Almacenar: memsvc.aremember("Aprender Python", payload)
# - WM: mt_wm.admit("sandbox", vec, payload)
# - HRR: mt_ctx.admit("sandbox", "Aprender Python", hrr_vec)

# 3. Respuesta
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns"
}
```

## Probando Operaciones de Memoria

```bash
# Almacenar una memoria
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{"payload": {"task": "Memoria de prueba", "memory_type": "episodic"}}'

# Recuperarla
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "Memoria de prueba", "top_k": 3}'
```

## Archivos Clave para Leer

1. `somabrain/app.py` - Endpoints API (remember, recall)
2. `somabrain/scoring.py` - Implementación UnifiedScorer
3. `somabrain/mt_wm.py` - Memoria de trabajo
4. `somabrain/services/memory_service.py` - Cliente backend
5. `somabrain/quantum.py` - Operaciones HRR
