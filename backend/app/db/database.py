from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# FastAPI senkron uç noktaları thread havuzunda çalıştırdığı için SQLite'ta thread kontrolü kapatılır
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


def init_db() -> None:
    """Eksik tabloları oluşturur (var olanlara dokunmaz)."""
    from app.db import tables  # noqa: F401  tabloları metadata'ya kaydeder

    Base.metadata.create_all(bind=engine)
