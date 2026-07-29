import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.database import Base

# Import every model module so they're registered on Base.metadata before
# `target_metadata` is read below -- required for autogenerate to see them.
import app.core.security_log  # noqa: F401
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql` -- emits SQL without a live DB connection."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Normal path: `alembic upgrade head` against the real (async) Neon
    connection. asyncpg has no sync driver, so migrations run inside
    `connection.run_sync(...)` rather than Alembic's default sync engine
    setup -- this is the standard pattern for an asyncpg-only project."""
    connectable = create_async_engine(DATABASE_URL, poolclass=None)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
