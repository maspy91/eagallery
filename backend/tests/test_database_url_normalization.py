from app.core.config import Settings


def test_settings_passes_database_url_through_unchanged() -> None:
    """SSL for the Postgres connection is handled via connect_args in
    app/core/database.py (ssl=require passed directly to asyncpg), not by
    rewriting the DATABASE_URL query string -- so Settings no longer
    transforms the URL at all. This replaces the older test that checked
    for a sslmode->ssl rewrite; that rewriting validator was removed from
    config.py, and the old test was failing as a result (asserting a
    transformation that no longer happens)."""
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:password@host/dbname?sslmode=require",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="test-secret-key",
        FRONTEND_URL="http://localhost:5173",
    )

    assert settings.DATABASE_URL == "postgresql+asyncpg://user:password@host/dbname?sslmode=require"
