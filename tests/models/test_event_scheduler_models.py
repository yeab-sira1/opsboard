"""Tests for the domain event and scheduled job models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models import (
    DomainEvent,
    DomainEventType,
    ScheduledJob,
    ScheduledJobStatus,
)


def test_create_domain_event_defaults(session: Session) -> None:
    event = DomainEvent(event_type=DomainEventType.ORDER_COMPLETED)
    session.add(event)
    session.flush()

    assert isinstance(event.id, uuid.UUID)
    assert event.event_type is DomainEventType.ORDER_COMPLETED
    assert event.payload_json == "{}"
    assert isinstance(event.created_at, datetime)


def test_domain_event_payload_is_stored(session: Session) -> None:
    event = DomainEvent(
        event_type=DomainEventType.REPORT_GENERATED,
        payload_json='{"report_type": "order_summary"}',
    )
    session.add(event)
    session.flush()

    assert event.payload_json == '{"report_type": "order_summary"}'


def test_create_scheduled_job_defaults(session: Session) -> None:
    job = ScheduledJob(
        job_name="nightly-report",
        scheduled_for=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session.add(job)
    session.flush()

    assert isinstance(job.id, uuid.UUID)
    assert job.status is ScheduledJobStatus.PENDING
    assert job.completed_at is None
    assert job.error_message is None


def test_all_event_types_persistable(session: Session) -> None:
    for event_type in DomainEventType:
        session.add(DomainEvent(event_type=event_type))
    session.flush()

    assert session.query(DomainEvent).count() == len(DomainEventType)
