"""Tests for the :class:`CacheEntry` model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import CacheEntry


def test_create_cache_entry_defaults(session: Session) -> None:
    entry = CacheEntry(cache_key="dashboard:inventory", payload_json="{}")
    session.add(entry)
    session.flush()

    assert isinstance(entry.id, uuid.UUID)
    assert entry.expires_at is None
    assert isinstance(entry.created_at, datetime)


def test_cache_key_is_unique(session: Session) -> None:
    session.add(CacheEntry(cache_key="dup", payload_json="{}"))
    session.flush()
    session.add(CacheEntry(cache_key="dup", payload_json="{}"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_expires_at_is_stored(session: Session) -> None:
    expires = datetime(2026, 1, 1, tzinfo=timezone.utc)
    entry = CacheEntry(
        cache_key="k", payload_json="{}", expires_at=expires
    )
    session.add(entry)
    session.flush()

    assert entry.expires_at == expires
