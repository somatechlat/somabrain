# Agente Cero: Primeros Pasos

**Propósito**: Poner en marcha un agente IA con SomaBrain en 5 minutos.

## Prerrequisitos

- Docker y Docker Compose instalados
- Servicio de memoria externo ejecutándose en `http://localhost:9595`
- 2GB RAM disponible

## Inicio Rápido (Pasos Verificados en Código)

### 1. Clonar e Iniciar

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker compose up -d
```

**Qué Hace Esto** (de `docker-compose.yml`):
- Inicia Redis en puerto 30100
- Inicia Kafka en puerto 30102
- Inicia OPA en puerto 30104
- Inicia Postgres en puerto 30106
- Inicia Prometheus en puerto 30105
- Inicia API SomaBrain en puerto 9696

### 2. Verificar Salud

```bash
curl http://localhost:9696/health | jq .
```

**Respuesta Esperada**:

```json
{
  "ok": true,
  "ready": true,
  "components": {
    "memory": {"http": true, "ok": true},
    "api_version": 1
  },
  "predictor_ok": true,
  "memory_ok": true,
  "embedder_ok": true,
  "kafka_ok": true,
  "postgres_ok": true,
  "opa_ok": true
}
```

### 3. Almacenar Tu Primera Memoria

```bash
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "task": "La Torre Eiffel está en París",
      "memory_type": "episodic"
    }
  }'
```

**Respuesta**:

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns"
}
```

### 4. Recuperar la Memoria

```bash
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Dónde está la Torre Eiffel?",
    "top_k": 3
  }' | jq .
```

**Respuesta**:

```json
{
  "wm": [
    {
      "score": 0.92,
      "payload": {
        "task": "La Torre Eiffel está en París",
        "memory_type": "episodic"
      }
    }
  ],
  "memory": [...],
  "namespace": "somabrain_ns"
}
```

## Entendiendo la Respuesta

### Memoria de Trabajo (wm)

- **Fuente**: Caché en memoria (`mt_wm`)
- **Capacidad**: 64 elementos por tenant (predeterminado)
- **Puntuación**: UnifiedScorer (coseno + FD + recencia)
- **Rápido**: Sin llamada a servicio externo

### Memoria a Largo Plazo (memory)

- **Fuente**: Servicio de memoria externo
- **Capacidad**: Ilimitada (dependiente del backend)
- **Persistencia**: Sobrevive reinicios
- **Más Lento**: Llamada HTTP al backend

## Conceptos Básicos de Configuración

### Variables de Entorno

**Requeridas**:

```bash
SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://localhost:9595"
SOMABRAIN_MEMORY_HTTP_TOKEN="devtoken"
```

**Opcionales**:

```bash
SOMABRAIN_MODE="full-local"  # o "prod"
SOMABRAIN_PREDICTOR_PROVIDER="mahal"  # mahal|slow|llm
SOMABRAIN_EMBED_PROVIDER="tiny"  # tiny|openai|...
```

### Archivo de Configuración (config.yaml)

```yaml
wm_size: 64
embed_dim: 256
use_hrr: false
rate_rps: 50.0
```

**Ubicación**: Raíz del proyecto

**Carga**: Automática vía `load_config()` en `somabrain/config.py`

## Problemas Comunes

### 1. Backend de Memoria No Disponible

**Error**:

```json
{
  "detail": {"message": "memory backend unavailable"}
}
```

**Solución**:

```bash
# Verificar que servicio de memoria esté ejecutándose
curl http://localhost:9595/health

# Verificar endpoint en config
echo $SOMABRAIN_MEMORY_HTTP_ENDPOINT
```

### 2. Verificación de Salud Falla

**Síntoma**: `"ready": false`

**Depurar**:

```bash
# Verificar componentes individuales
curl http://localhost:9696/health | jq '{
  memory_ok,
  kafka_ok,
  postgres_ok,
  opa_ok,
  embedder_ok,
  predictor_ok
}'
```

**Solución**: Iniciar servicios faltantes

```bash
docker compose up -d somabrain_kafka somabrain_postgres somabrain_opa
```

### 3. Límite de Tasa Excedido

**Error**: `429 Too Many Requests`

**Solución**: Ajustar límites de tasa

```bash
export SOMABRAIN_RATE_RPS=100
export SOMABRAIN_RATE_BURST=200
docker compose restart somabrain_app
```

## Próximos Pasos

1. **Leer [propagation-agent.md](propagation-agent.md)** - Profundizar en operaciones de memoria
2. **Leer [monitoring-agent.md](monitoring-agent.md)** - Configurar observabilidad
3. **Leer [security-hardening.md](security-hardening.md)** - Asegurar tu despliegue
4. **Explorar API** - Probar `/context/evaluate`, `/context/feedback`, `/plan/suggest`

## Referencia Rápida de Endpoints API

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/health` | GET | Verificación de salud |
| `/metrics` | GET | Métricas Prometheus |
| `/remember` | POST | Almacenar memoria |
| `/recall` | POST | Recuperar memoria |
| `/context/evaluate` | POST | Construir contexto |
| `/context/feedback` | POST | Actualizar pesos |
| `/plan/suggest` | POST | Generar plan |
| `/neuromodulators` | GET/POST | Obtener/establecer estado neuromodulador |

## Puntos de Entrada del Código

- **App Principal**: `somabrain/app.py`
- **Config**: `somabrain/config.py`
- **Memoria**: `somabrain/memory/`
- **Quantum/HRR**: `somabrain/quantum.py`
- **Puntuación**: `somabrain/scoring.py`
- **Aprendizaje**: `somabrain/learning/adaptation.py`

## Probando Tu Configuración

```bash
# Ejecutar tests de integración
pytest tests/integration/

# Ejecutar tests principales
pytest tests/core/

# Verificar calidad de código
ruff check somabrain/
mypy somabrain/
```

## Obteniendo Ayuda

- **Documentación**: Directorio `docs/`
- **Ejemplos**: Directorio `examples/`
- **Tests**: Directorio `tests/` (ejemplos de uso)
- **Issues**: GitHub Issues

## Criterios de Éxito

Estás listo para construir cuando:

- ✅ Endpoint de salud retorna `"ready": true`
- ✅ Puedes almacenar y recuperar una memoria
- ✅ Endpoint de métricas retorna datos Prometheus
- ✅ Todos los servicios Docker están saludables
- ✅ Entiendes el flujo básico de la API
