"""Veritabanı bağlantı motoru ve oturum yönetimi.
IBM DB2 ve yerel geliştirme için SQLite desteği sunar.
"""

from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


# SQLite için multi-thread erişim ayarı
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI Depends için veritabanı oturum üreticisi."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Tüm tabloları veritabanında otomatik olarak oluşturur."""
    from app.db import tables  # Modellerin Base'e kaydedilmesi için import edilmeli
    Base.metadata.create_all(bind=engine)
