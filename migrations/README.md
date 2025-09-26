Alembic migrations
==================

Use these commands for schema changes:

```
alembic upgrade head
alembic revision -m "message"
```

The environment reads Postgres DSNs from `SOMABRAIN_POSTGRES_DSN` / `SOMABRAIN_DB_URL`,
falling back to the local SQLite cache (`data/somabrain.db`).
