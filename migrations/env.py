from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from somabrain.storage import db
# Import the application settings to obtain the PostgreSQL DSN. This resolves a
# NameError that occurs during migration execution because ``settings`` was not
# defined in this module.
# Import settings lazily inside _get_url to avoid import-time side effects or
# circular import issues that can cause ``NameError: name 'settings' is not defined``

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
TARGET_METADATA = db.Base.metadata


def _get_url() -> str:
    """Return the PostgreSQL DSN for Alembic migrations.

    The function lazily imports the application ``settings`` to avoid import‑time
    side effects and circular import problems. It first checks the
    ``SOMABRAIN_POSTGRES_DSN`` environment variable (the same variable used by
    the application at runtime). If it is not set, it falls back to the default
    DSN provided by ``somabrain.storage.db.get_default_db_url``.
    """
    # Lazy import to prevent NameError during module import when settings
    # depends on other runtime components.
    from common.config.settings import settings

    return settings.postgres_dsn or db.get_default_db_url()


def run_migrations_offline() -> None:
    """Run Alembic migrations in *offline* mode.

    Offline mode generates SQL scripts without requiring a live database
    connection.  It is useful for CI pipelines that need to validate the
    migration scripts without a running PostgreSQL instance.
    """
    url = _get_url()
    context.configure(url=url, target_metadata=TARGET_METADATA, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run Alembic migrations in *online* mode.

    Online mode connects to the target database using the URL returned by
    :func:`_get_url` and applies the migrations directly.  It is the default
    mode used when ``alembic upgrade`` is executed against a live environment.
    """
    cfg = config.get_section(config.config_ini_section)
    connectable = engine_from_config(
        cfg, prefix="sqlalchemy.", poolclass=pool.NullPool, url=_get_url()
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=TARGET_METADATA)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
