"""Tests for :class:`ImportJobRepository`."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models import ImportJob, ImportJobStatus
from src.repositories import ImportJobRepository


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def test_get_by_status(session: Session) -> None:
    repo = ImportJobRepository(session)
    completed = repo.add(
        ImportJob(source_name="a.csv", status=ImportJobStatus.COMPLETED)
    )
    repo.add(ImportJob(source_name="b.csv", status=ImportJobStatus.FAILED))

    assert [j.id for j in repo.get_by_status(ImportJobStatus.COMPLETED)] == [
        completed.id
    ]
    assert len(repo.get_by_status(ImportJobStatus.FAILED)) == 1
    assert repo.get_by_status(ImportJobStatus.PENDING) == []


def test_get_recent_orders_newest_first(session: Session) -> None:
    repo = ImportJobRepository(session)
    repo.add(ImportJob(source_name="old.csv", created_at=_at(1)))
    newest = repo.add(ImportJob(source_name="new.csv", created_at=_at(3)))
    middle = repo.add(ImportJob(source_name="mid.csv", created_at=_at(2)))

    recent = repo.get_recent(limit=2)
    assert [j.id for j in recent] == [newest.id, middle.id]
