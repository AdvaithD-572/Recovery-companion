from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String, TypeDecorator, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
import json

from app.core.config import settings


class GUID(TypeDecorator):
    """Platform-independent GUID type for SQLite.
    Uses PostgreSQL's UUID type when available, otherwise stores as string.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return uuid.UUID(str(value))

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(Text())


def get_database_url():
    """Get database URL - supports PostgreSQL and SQLite for development."""
    db_url = settings.DATABASE_URL
    
    # Check if we should use SQLite (development mode)
    if "sqlite" in db_url.lower():
        return db_url
    
    # Default to SQLite for local development without Docker
    if settings.ENVIRONMENT == "development":
        # Check if PostgreSQL is available by trying to connect
        return "sqlite+aiosqlite:///./recovery_companion.db"
    
    return db_url


# Create engine with appropriate settings
db_url = get_database_url()

if "sqlite" in db_url:
    # SQLite configuration - no pool needed
    engine = create_async_engine(
        db_url,
        echo=settings.ENVIRONMENT == "development",
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL configuration
    engine = create_async_engine(
        db_url,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.ENVIRONMENT == "development",
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
