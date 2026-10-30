"""Database engine and session management (PostgreSQL only)."""

from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _postgres_url(raw_url: str) -> str:
    """Accept only PostgreSQL URLs and use the psycopg (v3) driver by default."""
    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError(
            f"DATABASE_URL must point to PostgreSQL (postgresql+psycopg://...); got '{url.drivername}'."
        )
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)


engine = create_engine(
    _postgres_url(settings.database_url),
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    """Provide a database session for FastAPI dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
