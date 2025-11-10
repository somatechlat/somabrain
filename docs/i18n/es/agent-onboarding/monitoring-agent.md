# Guía del Agente de Monitoreo

**Propósito**: Comprender observabilidad, métricas y verificaciones de salud en SomaBrain.

## Endpoint de Salud (Verificado en Código)

**Endpoint**: `GET /health`

**Implementación**: `somabrain/app.py` línea ~1900

**Estructura de Respuesta** (campos reales del código):

```json
{
  "ok": true,
  "components": {
    "memory": {"http": true, "ok": true},
    "wm_items": "tenant-scoped",
    "api_version": 1
  },
  "namespace": "somabrain_ns",
  "ready": true,
  "predictor_ok": true,
  "memory_ok": true,
  "embedder_ok": true,
  "kafka_ok": true,
  "postgres_ok": true,
  "opa_ok": true,
  "external_backends_required": true,
  "predictor_provider": "mahal",
  "embedder": {"provider": "tiny", "dim": 256},
  "memory_circuit_open": false
}
```

## Verificaciones de Preparación (Lógica Real)

**De endpoint health en `somabrain/app.py`**:

```python
# Enforcement de backend requiere:
predictor_ok = predictor_provider not in ("stub", "baseline")
memory_ok = memory_backend.health()["http"] == True
embedder_ok = embedder is not None
kafka_ok = check_kafka(kafka_url)  # somabrain/healthchecks.py
postgres_ok = check_postgres(pg_dsn)  # somabrain/healthchecks.py
opa_ok = opa_client.is_ready()

# Preparación general:
ready = predictor_ok and memory_ok and embedder_ok and kafka_ok and postgres_ok and opa_ok
```

## Endpoint de Métricas

**Endpoint**: `GET /metrics`

**Implementación**: `somabrain/metrics.py`

**Formato**: Formato de texto Prometheus

**Métricas Clave** (reales del código):

### Métricas de Solicitud
```
somabrain_http_request_duration_seconds{method="POST",path="/recall"}
somabrain_http_requests_total{method="POST",path="/recall",status="200"}
```

### Métricas de Memoria
```
somabrain_wm_hits_total
somabrain_wm_misses_total
somabrain_wm_utilization
somabrain_recall_cache_hit_total{cohort="baseline"}
somabrain_recall_cache_miss_total{cohort="baseline"}
```

### Métricas de Puntuación
```
somabrain_scorer_component{component="cosine"}
somabrain_scorer_component{component="fd"}
somabrain_scorer_component{component="recency"}
somabrain_scorer_final
```

### Métricas de Aprendizaje
```
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="alpha"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="beta"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="gamma"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="tau"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="lambda"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="mu"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="nu"}
```

### Métricas HRR
```
somabrain_hrr_cleanup_calls_total
somabrain_hrr_cleanup_used_total
somabrain_hrr_cleanup_score
somabrain_hrr_anchor_size
somabrain_hrr_context_saturation
somabrain_hrr_rerank_applied_total
```

## Configuración de Prometheus

**Archivo**: `ops/prometheus/etc/prometheus.yml`

**Config de Scrape**:

```yaml
scrape_configs:
  - job_name: 'somabrain'
    static_configs:
      - targets: ['somabrain_app:9696']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Implementación de Verificación de Salud

**Archivo**: `somabrain/healthchecks.py`

### Verificación Kafka

```python
def check_kafka(kafka_url: str) -> bool:
    """Verificar que broker Kafka sea alcanzable."""
    # Implementación real usa AdminClient
    # Retorna True si broker responde
```

### Verificación Postgres

```python
def check_postgres(dsn: str) -> bool:
    """Verificar conexión Postgres."""
    # Implementación real usa psycopg2
    # Retorna True si conexión exitosa
```

## Circuit Breaker (Servicio de Memoria)

**Archivo**: `somabrain/services/memory_service.py`

**Variables de Estado** (nivel de clase):

```python
_circuit_open: bool = False
_failure_count: int = 0
_last_failure_time: float = 0.0
_failure_threshold: int = 3
_reset_interval: int = 60  # segundos
```

**Lógica**:

```python
# En fallo:
_failure_count += 1
if _failure_count >= _failure_threshold:
    _circuit_open = True
    _last_failure_time = time.time()

# En éxito:
_failure_count = 0
_circuit_open = False

# Auto-reset después de intervalo:
if _circuit_open and (time.time() - _last_failure_time) > _reset_interval:
    _circuit_open = False
    _failure_count = 0
```

## Configuración de Logging

**Archivo**: `somabrain/app.py` (función setup_logging)

**Niveles de Log**:
- `INFO`: Eventos generales del sistema
- `DEBUG`: Detalles de procesamiento cognitivo
- `ERROR`: Manejo de errores

**Salida de Log**:
- Consola (stdout)
- Archivo: `/app/logs/somabrain.log` (si escribible)

**Formato**:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Stack de Observabilidad (Docker Compose)

| Componente | Puerto | Propósito |
|------------|--------|-----------|
| Prometheus | 30105 | Recolección de métricas |
| Jaeger | 30011 | Trazado distribuido |
| Kafka Exporter | 30103 | Métricas Kafka |
| Postgres Exporter | 30107 | Métricas Postgres |

## Ejemplo: Flujo de Monitoreo

```bash
# 1. Verificar salud
curl http://localhost:9696/health | jq .

# 2. Verificar preparación
curl http://localhost:9696/health | jq '.ready'

# 3. Scrape métricas
curl http://localhost:9696/metrics | grep somabrain_

# 4. Consultar Prometheus
curl 'http://localhost:30105/api/v1/query?query=somabrain_http_requests_total'

# 5. Verificar circuit breaker
curl http://localhost:9696/health | jq '.memory_circuit_open'
```

## Condiciones de Alerta (Recomendadas)

Basadas en métricas reales:

```yaml
# Tasa alta de errores
- alert: HighErrorRate
  expr: rate(somabrain_http_requests_total{status=~"5.."}[5m]) > 0.05

# Backend de memoria caído
- alert: MemoryBackendDown
  expr: somabrain_health_memory_ok == 0

# Circuit breaker abierto
- alert: CircuitBreakerOpen
  expr: somabrain_memory_circuit_open == 1

# Utilización WM alta
- alert: WMUtilizationHigh
  expr: somabrain_wm_utilization > 0.9
```

## Archivos Clave para Leer

1. `somabrain/app.py` - Implementación endpoint health
2. `somabrain/metrics.py` - Definiciones de métricas
3. `somabrain/healthchecks.py` - Funciones de verificación de salud
4. `somabrain/services/memory_service.py` - Circuit breaker
5. `ops/prometheus/etc/prometheus.yml` - Config Prometheus
