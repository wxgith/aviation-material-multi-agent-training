from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Base


def _connect_args() -> dict:
    database_url = settings.database_url.lower()
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    if database_url.startswith(("mysql+", "postgresql+")):
        return {"connect_timeout": 3}
    return {}


@lru_cache
def get_engine():
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_timeout=3,
        connect_args=_connect_args(),
    )


@lru_cache
def get_session_factory():
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def database_connected() -> bool:
    if not settings.database_enabled:
        return False
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@contextmanager
def session_scope():
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_cache() -> None:
    get_engine.cache_clear()
    get_session_factory.cache_clear()
