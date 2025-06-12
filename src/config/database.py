"""Database engine and session configuration for opsboard."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base

DEFAULT_DATABASE_URL = "sqlite+pysqlite:///:memory:"


def create_database_engine(
    url: str = DEFAULT_DATABASE_URL, *, echo: bool = False
) -> Engine:
    """Create a SQLAlchemy :class:`Engine` for the given database URL."""
    return create_engine(url, echo=echo)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    """Create all tables registered on the declarative ``Base``."""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    Commits on success, rolls back on error, and always closes the session.
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
