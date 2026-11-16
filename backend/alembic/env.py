import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your models' Base for autogenerate support
from app.core.database import Base
from app.models import *  # noqa - Import all models to register them with Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
from app import care  # register clinic tables
from app import registry
from app.core.config import settings
config = context.config
config.set_main_option("sqlalchemy.url",settings.DATABASE_URL.replace("%","%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None and config.attributes.get('connection') is None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        from sqlalchemy import inspect
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        from alembic.script import ScriptDirectory
        tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
        migration = context.get_context()
        if tables and not migration.get_current_heads():
            complete = set(target_metadata.tables)
            legacy = {name for name in complete if not name.startswith("care_")}
            original_clinic = legacy | {"care_staff", "care_links", "care_invites", "care_records"}
            recognized = {frozenset(legacy): "0000", frozenset(original_clinic): "0001",
                          frozenset(complete): "0002"}
            if frozenset(tables) not in recognized:
                raise RuntimeError("Unversioned database has an unknown table set. Restore a backup and review the schema.")
            # Only adopt a recognized prototype schema; never infer clinic consent.
            def included(obj, name, kind, reflected, compare_to):
                return kind != "table" or name in tables
            inspection = MigrationContext.configure(connection, opts={"include_object":included,"compare_type":True})
            if compare_metadata(inspection,target_metadata):
                raise RuntimeError("Unversioned database differs from the known schema.")
            migration.stamp(ScriptDirectory.from_config(config), recognized[frozenset(tables)])
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    supplied = config.attributes.get('connection')
    if supplied is None:
        asyncio.run(run_async_migrations())
    else:
        do_run_migrations(supplied)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
