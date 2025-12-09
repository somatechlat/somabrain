# Configuration

This document provides an overview of the configuration options for SomaBrain, including environment variables and settings files.

## Environment Variables

SomaBrain uses a centralized `Settings` class (based on Pydantic's `BaseSettings`) to manage configuration. This class loads values from a `.env` file or from environment variables.

### Core Infrastructure

| Variable | Type | Default | Description |
|---|---|---|---|
| `SOMABRAIN_POSTGRES_DSN` | string | "" | The Data Source Name for the PostgreSQL database. |
| `SOMABRAIN_REDIS_URL` or `REDIS_URL` | string | "" | The URL for the Redis instance. |
| `SOMABRAIN_KAFKA_URL` or `KAFKA_BOOTSTRAP_SERVERS` | string | "" | The bootstrap servers for the Kafka cluster. |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | string | "http://localhost:9696" | The endpoint for the external memory service. |
| `SOMABRAIN_MEMORY_HTTP_TOKEN` | string | "" | The authentication token for the external memory service. |

### Authentication

| Variable | Type | Default | Description |
|---|---|---|---|
| `SOMABRAIN_AUTH_REQUIRED` | boolean | `False` | Whether to enforce bearer-token authentication. |
| `SOMABRAIN_API_TOKEN` | string | "" | The static token value when `SOMABRAIN_AUTH_REQUIRED` is `True`. |
| `SOMABRAIN_JWT_SECRET` | string | "" | The secret for JWT token validation. |

### Learning and Adaptation

| Variable | Type | Default | Description |
|---|---|---|---|
| `SOMABRAIN_LEARNING_RATE_DYNAMIC` | boolean | `False` | Whether to enable dynamic learning rate scaling based on neuromodulator levels. |
| `SOMABRAIN_ADAPT_LR` | float | `0.05` | The base learning rate for the adaptation engine. |

For a complete list of all environment variables and their default values, please refer to the `common/config/settings.py` file.

## Per-Tenant Overrides

The learning and adaptation parameters can be overridden on a per-tenant basis using a YAML or JSON file. The path to this file is specified by the `SOMABRAIN_LEARNING_TENANTS_FILE` environment variable.

The file should be structured as follows:

```yaml
tenant_id:
  tau_decay_rate: 0.02
  entropy_cap: 1.25
```

Supported keys:
- `tau_decay_rate` (float)
- `entropy_cap` (float)

Missing keys will fall back to the global environment settings.
