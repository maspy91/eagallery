from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

settings = get_settings()

# Neon requires SSL; asyncpg reads that from the connection string itself
# (postgresql+asyncpg://...?ssl=require). pool_pre_ping guards against
# Neon's serverless compute suspending an idle connection between requests.

# engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True, pool_pre_ping=True)


engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"ssl": "require"}, 
    # Required for Neon/Supabase cloud instances
    pool_pre_ping=True,               # Checks if connection is alive before querying
    pool_recycle=300,    # Recycles connections older than 5 minutes (prevents dropouts)
    pool_size=10,                      # Keeps a steady pool size
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session