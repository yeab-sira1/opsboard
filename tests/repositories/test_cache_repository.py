"""Tests for :class:`CacheRepository`."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models import CacheEntry
from src.repositories import CacheRepository


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def test_get_by_key(session: Session) -> None:
    repo = CacheRepository(session)
    entry = repo.add(CacheEntry(cache_key="k1", payload_json="{}"))

    assert repo.get_by_key("k1") is entry
    assert repo.get_by_key("missing") is None


def test_get_expired_excludes_null_and_future(session: Session) -> None:
    repo = CacheRepository(session)
    expired = repo.add(
        CacheEntry(cache_key="old", payload_json="{}", expires_at=_at(1))
    )
    repo.add(
        CacheEntry(cache_key="future", payload_json="{}", expires_at=_at(10))
    )
    repo.add(CacheEntry(cache_key="never", payload_json="{}"))

    result = repo.get_expired(_at(5))
    assert [e.id for e in result] == [expired.id]


def test_get_expired_is_inclusive_of_boundary(session: Session) -> None:
    repo = CacheRepository(session)
    boundary = repo.add(
        CacheEntry(cache_key="b", payload_json="{}", expires_at=_at(5))
    )

    assert [e.id for e in repo.get_expired(_at(5))] == [boundary.id]


def test_delete_by_key(session: Session) -> None:
    repo = CacheRepository(session)
    repo.add(CacheEntry(cache_key="k1", payload_json="{}"))

    assert repo.delete_by_key("k1") is True
    assert repo.get_by_key("k1") is None
    assert repo.delete_by_key("k1") is False
