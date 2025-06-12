"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from src.config.database import (
    create_database_engine,
    create_session_factory,
    init_database,
)


@pytest.fixture
def session() -> Iterator[Session]:
    """Provide a session backed by a fresh in-memory SQLite database."""
    engine = create_database_engine()
    init_database(engine)
    session_factory = create_session_factory(engine)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()
