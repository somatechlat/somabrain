# Clasificación de Seguridad de Documentos

Este documento define las clasificaciones de seguridad para la documentación de SomaBrain según los requisitos de ISO/IEC 27001.

## Niveles de Clasificación

| Nivel | Descripción | Manejo | Ejemplos |
|-------|-------------|--------|----------|
| **PÚBLICO** | Información que puede compartirse abiertamente | Sin restricciones | Documentación de API, diagramas de arquitectura, guías de usuario |
| **INTERNO** | Detalles operacionales para uso del equipo | Mantener en repositorio público con marcadores `<!-- INTERNO -->` | Configuraciones de despliegue interno, flujos de trabajo de desarrollo |
| **CONFIDENCIAL** | Información sensible | Almacenar solo en repositorio privado; usar placeholders en docs públicos | Credenciales de producción, detalles de vulnerabilidades, datos de clientes |

## Clasificaciones de Documentos Actuales

### Documentos PÚBLICOS

- Todos los archivos en `docs/user-manual/`
- Todos los archivos en `docs/technical-manual/` (excepto security/)
- Todos los archivos en `docs/development-manual/`
- Todos los archivos en `docs/onboarding-manual/`
- `README.md`
- `ROADMAP_*.md`

### Documentos INTERNOS

- `docs/technical-manual/security/` (procedimientos de seguridad operacional)
- `docs/operational/` (listas de verificación de despliegue, runbooks)

### Documentos CONFIDENCIALES

**Ninguno en repositorio público**

Toda información confidencial usa placeholders:
- `<MEMORY_SERVICE_TOKEN>` en lugar de tokens reales
- `<POSTGRES_PASSWORD>` en lugar de contraseñas reales
- `<JWT_SECRET>` en lugar de secretos de producción

## Manejo de Credenciales

### En Documentación

**NUNCA incluir:**
- Tokens de API reales
- Contraseñas de producción
- Claves privadas
- Datos de clientes
- Direcciones IP internas (usar placeholder `<IP_INTERNA>`)

**SIEMPRE usar:**
- `devtoken` para ejemplos de desarrollo
- Placeholders `<TOKEN>` para producción
- `localhost` o `127.0.0.1` para ejemplos locales
- Nombres de servicio `somabrain_*` para ejemplos de Docker Compose

### En Ejemplos de Código

```bash
# ✅ CORRECTO - Usa placeholder
export SOMABRAIN_MEMORY_HTTP_TOKEN="<TU_TOKEN_AQUI>"

# ❌ INCORRECTO - Token real
export SOMABRAIN_MEMORY_HTTP_TOKEN="sk-prod-abc123..."
```

## Verificación

Todos los commits de documentación se escanean para:
- Credenciales hardcodeadas (patrones regex)
- Direcciones IP privadas
- Nombres de host internos
- Información específica de clientes

## Respuesta a Incidentes

Si información confidencial se commitea accidentalmente:

1. **Inmediatamente** rotar la credencial expuesta
2. Eliminar del historial de git usando `git filter-branch` o BFG Repo-Cleaner
3. Documentar incidente en registro de seguridad
4. Notificar a partes afectadas

## Última Actualización

2025-01-XX
