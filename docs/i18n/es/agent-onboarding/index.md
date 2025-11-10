# Guía de Incorporación para Agentes

**Propósito**: Permitir que agentes IA comprendan y trabajen efectivamente con el código base de SomaBrain.

## Datos Rápidos (Verificados en Código)

| Propiedad | Valor | Fuente |
|-----------|-------|--------|
| **Archivo API Principal** | `somabrain/app.py` | Aplicación FastAPI |
| **Puerto API** | 9696 (host y contenedor) | `docker-compose.yml` |
| **Sistema de Config** | `somabrain/config.py` | Basado en dataclass con overrides de env |
| **Dimensión de Memoria** | 256 (default `embed_dim`) | Dataclass `Config` |
| **Dimensión HRR** | 8192 (default `hrr_dim`) | Dataclass `Config` |
| **Tamaño Memoria de Trabajo** | 64 (default `wm_size`) | Dataclass `Config` |

## Componentes Principales (Ubicaciones Reales)

### 1. Capa API
- **Archivo**: `somabrain/app.py`
- **Framework**: FastAPI
- **Endpoints Clave**:
  - `POST /remember` - Almacenar memoria
  - `POST /recall` - Recuperar memoria
  - `POST /context/evaluate` - Construir contexto
  - `POST /context/feedback` - Actualizar pesos
  - `GET /health` - Verificación de salud

### 2. Configuración
- **Archivo**: `somabrain/config.py`
- **Clase**: `Config` (dataclass)
- **Carga**: Función `load_config()`
- **Prefijo Env**: `SOMABRAIN_`

### 3. Capa Quantum/HRR
- **Archivo**: `somabrain/quantum.py`
- **Clase**: `QuantumLayer`
- **Matemáticas**: BHDC (Binary Hyperdimensional Computing)
- **Operaciones**: `bind()`, `unbind()`, `superpose()`

### 4. Sistema de Memoria
- **Superposed Trace**: `somabrain/memory/superposed_trace.py`
- **Jerárquica**: `somabrain/memory/hierarchical.py`
- **Clases**: `SuperposedTrace`, `TieredMemory`

### 5. Puntuación
- **Archivo**: `somabrain/scoring.py`
- **Clase**: `UnifiedScorer`
- **Componentes**: Coseno + FD + Recencia

### 6. Aprendizaje/Adaptación
- **Archivo**: `somabrain/learning/adaptation.py`
- **Clase**: `AdaptationEngine`
- **Pesos**: Recuperación (α, β, γ, τ) + Utilidad (λ, μ, ν)

## Variables de Entorno (Valores Predeterminados Reales)

```bash
# Backend de Memoria (REQUERIDO)
SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://localhost:9595"
SOMABRAIN_MEMORY_HTTP_TOKEN="devtoken"

# Redis
SOMABRAIN_REDIS_URL="redis://localhost:30100"

# Kafka
SOMABRAIN_KAFKA_URL="somabrain_kafka:9092"

# Postgres
SOMABRAIN_POSTGRES_DSN="postgresql://soma:soma@localhost:30106/somabrain"

# OPA
SOMABRAIN_OPA_URL="http://localhost:30104"

# Modo
SOMABRAIN_MODE="full-local"  # o "prod"

# Predictor
SOMABRAIN_PREDICTOR_PROVIDER="mahal"  # mahal|slow|llm
```

## Puertos Docker Compose (Verificados)

| Servicio | Puerto Host | Puerto Contenedor | Nombre Interno |
|----------|-------------|-------------------|----------------|
| API | 9696 | 9696 | somabrain_app |
| Redis | 30100 | 6379 | somabrain_redis |
| Kafka | 30102 | 9092 | somabrain_kafka |
| OPA | 30104 | 8181 | somabrain_opa |
| Prometheus | 30105 | 9090 | somabrain_prometheus |
| Postgres | 30106 | 5432 | somabrain_postgres |
| Schema Registry | 30108 | 8081 | somabrain_schema_registry |

## Próximos Pasos

1. Leer [propagation-agent.md](propagation-agent.md) para operaciones de memoria
2. Leer [monitoring-agent.md](monitoring-agent.md) para observabilidad
3. Leer [security-hardening.md](security-hardening.md) para prácticas de seguridad

## Consejos de Navegación de Código

- **Empezar aquí**: `somabrain/app.py` (app FastAPI principal)
- **Config**: `somabrain/config.py` (todas las configuraciones)
- **Matemáticas**: `somabrain/quantum.py` (operaciones BHDC)
- **Memoria**: `somabrain/memory/` (abstracciones de almacenamiento)
- **Tests**: `tests/` (ejemplos de uso)
