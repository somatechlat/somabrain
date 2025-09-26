import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from somabrain.storage import db  # noqa: F401
from somabrain.storage import feedback  # noqa: F401
from somabrain.storage import token_ledger  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

TARGET_METADATA = db.Base.metadata


def _get_url() -> str:
    return (
        os.getenv("SOMABRAIN_POSTGRES_DSN")
        or os.getenv("SOMABRAIN_DB_URL")
        or db.get_default_db_url()
    )


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(url=url, target_metadata=TARGET_METADATA, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section)
    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=_get_url(),
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=TARGET_METADATA)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
