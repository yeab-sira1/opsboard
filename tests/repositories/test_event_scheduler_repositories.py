"""Tests for the domain event and scheduled job repositories."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models import (
    DomainEvent,
    DomainEventType,
    ScheduledJob,
    ScheduledJobStatus,
)
from src.repositories import DomainEventRepository, ScheduledJobRepository


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def test_domain_event_type_and_recent_queries(session: Session) -> None:
    repo = DomainEventRepository(session)
    repo.add(
        DomainEvent(
            event_type=DomainEventType.ORDER_COMPLETED, created_at=_at(1)
        )
    )
    newest = repo.add(
        DomainEvent(
            event_type=DomainEventType.REPORT_GENERATED, created_at=_at(3)
        )
    )
    middle = repo.add(
        DomainEvent(
            event_type=DomainEventType.NOTIFICATION_SENT, created_at=_at(2)
        )
    )

    assert len(repo.get_by_event_type(DomainEventType.ORDER_COMPLETED)) == 1
    assert repo.get_by_event_type(DomainEventType.ORDER_CANCELLED) == []

    recent = repo.get_recent(limit=2)
    assert [e.id for e in recent] == [newest.id, middle.id]


def test_scheduled_job_status_queries(session: Session) -> None:
    repo = ScheduledJobRepository(session)
    pending = repo.add(
        ScheduledJob(job_name="a", scheduled_for=_at(1))
    )
    repo.add(
        ScheduledJob(
            job_name="b",
            scheduled_for=_at(1),
            status=ScheduledJobStatus.COMPLETED,
        )
    )

    assert [j.id for j in repo.get_pending_jobs()] == [pending.id]
    assert len(repo.get_by_status(ScheduledJobStatus.COMPLETED)) == 1
    assert repo.get_by_status(ScheduledJobStatus.FAILED) == []
