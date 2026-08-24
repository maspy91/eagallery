from app.core.config import Settings


def test_settings_normalize_sslmode_for_asyncpg() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:password@host/dbname?sslmode=require",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="test-secret-key",
    )

    assert settings.DATABASE_URL == "postgresql+asyncpg://user:password@host/dbname?ssl=require"
