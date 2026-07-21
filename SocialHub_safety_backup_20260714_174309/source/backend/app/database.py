"""Database connection setup for SocialHub.

This file is intentionally small and beginner-friendly:

- engine: talks to PostgreSQL using SQLAlchemy
- SessionLocal: creates database sessions for API requests
- Base: parent class used by all SQLAlchemy models/tables
- get_db: FastAPI dependency that opens/closes a session safely

The database URL comes from SocialHub/.env through app.config.settings.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Every model class inherits from this Base so SQLAlchemy knows which
    tables exist when Base.metadata.create_all(bind=engine) is called.
    """

    pass


# Synchronous SQLAlchemy engine used by normal FastAPI endpoints.
# pool_pre_ping=True checks connections before using them, which helps avoid
# stale/broken connection errors while developing in VS Code.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)


# Factory for database sessions.
# autocommit=False means we manually commit changes.
# autoflush=False avoids automatic writes before every query.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Provide one database session per request and close it afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Async database support for async endpoints or future background jobs.
async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=False,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_db():
    """Provide one async database session and close it afterwards."""

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_db():
    """Create all tables that are defined in app.models.models.

    Important: import app.models.models before calling this function in scripts,
    so SQLAlchemy registers every table on Base.metadata.
    """

    Base.metadata.create_all(bind=engine)