# Guía de Endurecimiento de Seguridad

**Propósito**: Comprender controles de seguridad y mejores prácticas en SomaBrain.

## Autenticación (Verificada en Código)

**Implementación**: `somabrain/auth.py`

### Auth con Token Bearer

```python
def require_auth(request: Request, cfg: Config) -> None:
    """Validar token Bearer del header Authorization."""
    # Verifica: Authorization: Bearer <token>
    # Valida contra cfg.api_token o JWT
```

### Auth de Admin

```python
def require_admin_auth(request: Request, cfg: Config) -> None:
    """Requerir autenticación nivel admin."""
    # Verificaciones adicionales para endpoints admin
```

### Soporte JWT

**Config** (de `somabrain/config.py`):

```python
jwt_secret: Optional[str] = None
jwt_public_key_path: Optional[str] = None
jwt_issuer: Optional[str] = None
jwt_audience: Optional[str] = None
```

**Variables de Entorno**:
```bash
SOMABRAIN_JWT_SECRET="<secret>"
SOMABRAIN_JWT_PUBLIC_KEY_PATH="/path/to/key.pem"
SOMABRAIN_JWT_ISSUER="somabrain"
SOMABRAIN_JWT_AUDIENCE="api"
```

## Aislamiento de Tenants

**Implementación**: `somabrain/tenant.py`

```python
def get_tenant(request: Request, default_namespace: str) -> TenantContext:
    """Extraer ID de tenant del header X-Tenant-ID o claims JWT."""
    # Retorna: TenantContext(tenant_id, namespace)
```

**Headers**:
```
X-Tenant-ID: sandbox
```

**Garantías de Aislamiento**:
- Memoria de trabajo es por tenant (`mt_wm.recall(tenant_id, ...)`)
- Contexto HRR es por tenant (`mt_ctx.cleanup(tenant_id, ...)`)
- Estado de adaptación es por tenant (claves Redis: `adaptation:state:{tenant_id}`)

## Límite de Tasa

**Implementación**: `somabrain/ratelimit.py`

**Config** (de `somabrain/config.py`):

```python
rate_rps: float = 50.0      # Solicitudes por segundo
rate_burst: int = 100       # Capacidad de ráfaga
```

**Uso** (de `somabrain/app.py`):

```python
if not rate_limiter.allow(ctx.tenant_id):
    raise HTTPException(status_code=429, detail="rate limit exceeded")
```

## Cuotas

**Implementación**: `somabrain/quotas.py`

**Config**:

```python
write_daily_limit: int = 10000  # Máx escrituras por tenant por día
```

**Uso**:

```python
if not quotas.allow_write(ctx.tenant_id, 1):
    raise HTTPException(status_code=429, detail="daily write quota exceeded")
```

## Enforcement de Políticas OPA

**Servicio**: `somabrain_opa` (Docker Compose)

**Puerto**: 30104 (host) → 8181 (contenedor)

**Políticas**: `ops/opa/policies/`

**Middleware**: `somabrain/api/middleware/opa.py`

**Verificación de Salud**:

```python
opa_ok = opa_client.is_ready()  # Requerido para preparación
```

## Validación de Entrada

**Implementación**: `somabrain/app.py` (CognitiveInputValidator)

### Validación de Texto

```python
SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.,!?\'\"()/:_@-]+$")
MAX_TEXT_LENGTH = 10000

def validate_text_input(text: str, field_name: str = "text") -> str:
    """Validar entrada de texto para procesamiento cognitivo."""
    # Verifica: longitud, caracteres seguros
```

### Validación de Coordenadas

```python
def validate_coordinates(coords: tuple) -> tuple:
    """Validar tuplas de coordenadas para procesamiento cerebral."""
    # Verifica: exactamente 3 floats, magnitud razonable
```

### Sanitización de Consultas

```python
def sanitize_query(query: str) -> str:
    """Sanitizar y preparar consulta para procesamiento cognitivo."""
    # Elimina: patrones <>, javascript:, data:
```

## Middleware de Seguridad

**Implementación**: `somabrain/app.py` (SecurityMiddleware)

**Patrones Bloqueados**:

```python
suspicious_patterns = [
    re.compile(r"union\s+select", re.IGNORECASE),  # Inyección SQL
    re.compile(r";\s*drop", re.IGNORECASE),        # Inyección SQL
    re.compile(r"<script", re.IGNORECASE),         # XSS
    re.compile(r"eval\s*\(", re.IGNORECASE),       # Inyección de código
]
```

**Respuesta**: 403 Forbidden

## Seguridad Docker (docker-compose.yml)

### Eliminación de Capacidades

```yaml
cap_drop: ["ALL"]  # Eliminar todas las capacidades Linux
```

### Sistema de Archivos de Solo Lectura

```yaml
read_only: true  # Prevenir modificaciones de archivos en runtime
```

### Sin Nuevos Privilegios

```yaml
security_opt:
  - no-new-privileges:true  # Prevenir escalada de privilegios
```

### Montajes Tmpfs

```yaml
tmpfs:
  - /app/logs  # Logs escribibles sin almacenamiento persistente
  - /tmp       # Archivos temporales
```

## Gestión de Secretos

### Variables de Entorno (Desarrollo)

```bash
# ✅ CORRECTO - Usar placeholders en docs
SOMABRAIN_MEMORY_HTTP_TOKEN="<TU_TOKEN>"

# ❌ INCORRECTO - Nunca commitear tokens reales
SOMABRAIN_MEMORY_HTTP_TOKEN="sk-prod-abc123..."
```

### Secretos de Producción

**Recomendado**: Usar gestores de secretos externos

- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets

**Nunca**:
- Hardcodear en código fuente
- Commitear a git
- Loguear a stdout

## Logging de Auditoría

**Implementación**: `somabrain/audit.py`

**Tópico Kafka**: `soma.audit`

**Eventos Logueados**:
- Acciones admin (`log_admin_action`)
- Fallos de autenticación
- Violaciones de políticas

**Ejemplo**:

```python
audit.log_admin_action(request, "neuromodulators_set", {
    "tenant": tenant_id,
    "new_state": {...}
})
```

## Seguridad de Red (Docker Compose)

**Red Interna**: `somabrain_net` (bridge)

**Puertos Expuestos** (acceso host):
- 9696: API (requerido)
- 30100-30108: Infraestructura (opcional, puede eliminarse en prod)

**Servicios Solo Internos**:
- Broker Kafka: `somabrain_kafka:9092` (no expuesto a host por defecto)
- Redis: `somabrain_redis:6379` (expuesto para dev, debe ser interno en prod)

## Lista de Verificación de Seguridad

### Antes del Despliegue

- [ ] Rotar todas las credenciales predeterminadas
- [ ] Habilitar autenticación JWT (`SOMABRAIN_JWT_SECRET`)
- [ ] Configurar políticas OPA
- [ ] Establecer límites de tasa por tenant
- [ ] Habilitar logging de auditoría a Kafka
- [ ] Revisar puertos expuestos
- [ ] Usar sistema de archivos de solo lectura
- [ ] Eliminar todas las capacidades
- [ ] Habilitar TLS para endpoints externos

### Monitoreo en Runtime

- [ ] Monitorear intentos de auth fallidos
- [ ] Rastrear violaciones de límite de tasa
- [ ] Alertar en aperturas de circuit breaker
- [ ] Revisar logs de auditoría diariamente
- [ ] Verificar decisiones de políticas OPA

## Archivos Clave para Leer

1. `somabrain/auth.py` - Lógica de autenticación
2. `somabrain/tenant.py` - Aislamiento de tenants
3. `somabrain/ratelimit.py` - Límite de tasa
4. `somabrain/quotas.py` - Enforcement de cuotas
5. `somabrain/app.py` - Validación de entrada, middleware de seguridad
6. `ops/opa/policies/` - Definiciones de políticas OPA
7. `docker-compose.yml` - Configuraciones de seguridad de contenedores
