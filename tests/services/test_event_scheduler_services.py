"""Tests for :class:`EventService` and :class:`SchedulerService`."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from src.models import (
    DomainEventType,
    NotificationStatus,
    ReportJobStatus,
    ReportRequest,
    ReportType,
    ScheduledJobStatus,
)
from src.services import (
    EventService,
    InvalidScheduledJobStateError,
    NotificationService,
    ReportJobService,
    ScheduledJobNotFoundError,
    SchedulerService,
)


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


# --- EventService --------------------------------------------------------


@pytest.fixture
def events(session: Session) -> EventService:
    return EventService(session)


def test_record_event_with_payload(events: EventService) -> None:
    event = events.record_event(
        DomainEventType.ORDER_COMPLETED, {"order_id": "abc"}
    )
    assert event.event_type is DomainEventType.ORDER_COMPLETED
    assert json.loads(event.payload_json) == {"order_id": "abc"}


def test_record_event_defaults_empty_payload(events: EventService) -> None:
    event = events.record_event(DomainEventType.ORDER_CANCELLED)
    assert event.payload_json == "{}"


def test_get_events_by_type_and_recent(events: EventService) -> None:
    events.record_event(DomainEventType.ORDER_COMPLETED)
    events.record_event(DomainEventType.ORDER_COMPLETED)
    events.record_event(DomainEventType.REPORT_GENERATED)

    assert len(events.get_events_by_type(DomainEventType.ORDER_COMPLETED)) == 2
    assert len(events.get_recent_events()) == 3


# --- SchedulerService ----------------------------------------------------


@pytest.fixture
def scheduler(session: Session) -> SchedulerService:
    return SchedulerService(session)


def _pending_report_job(session: Session) -> None:
    request = ReportRequest(report_type=ReportType.ORDER_SUMMARY)
    session.add(request)
    session.flush()
    ReportJobService(session).create_job(request.id)


def test_scheduler_success_path_records_events(
    session: Session,
    scheduler: SchedulerService,
    events: EventService,
) -> None:
    _pending_report_job(session)

    job = scheduler.create_job("nightly", _at(1))
    run = scheduler.run_job(job.id)

    assert run.status is ScheduledJobStatus.COMPLETED
    assert run.completed_at is not None
    # One report generated, then its success notification sent.
    assert len(events.get_events_by_type(DomainEventType.REPORT_GENERATED)) == 1
    assert (
        len(events.get_events_by_type(DomainEventType.NOTIFICATION_SENT)) == 1
    )


def test_scheduler_marks_report_jobs_and_notifications_done(
    session: Session, scheduler: SchedulerService
) -> None:
    _pending_report_job(session)
    job = scheduler.create_job("nightly", _at(1))
    scheduler.run_job(job.id)

    report_jobs = ReportJobService(session)
    notifications = NotificationService(session)
    assert report_jobs.get_jobs_by_status(ReportJobStatus.PENDING) == []
    assert (
        notifications.get_notifications_by_status(NotificationStatus.PENDING)
        == []
    )
    assert (
        len(
            notifications.get_notifications_by_status(NotificationStatus.SENT)
        )
        == 1
    )


def test_scheduler_failure_path_records_error(
    scheduler: SchedulerService,
) -> None:
    # Blank job name triggers a SchedulerExecutionError inside _execute.
    job = scheduler.create_job("   ", _at(1))
    run = scheduler.run_job(job.id)

    assert run.status is ScheduledJobStatus.FAILED
    assert run.error_message is not None
    assert run.completed_at is not None


def test_scheduler_invalid_state(scheduler: SchedulerService) -> None:
    job = scheduler.create_job("nightly", _at(1))
    scheduler.run_job(job.id)
    with pytest.raises(InvalidScheduledJobStateError):
        scheduler.run_job(job.id)


def test_scheduler_fail_job(scheduler: SchedulerService) -> None:
    job = scheduler.create_job("nightly", _at(1))
    failed = scheduler.fail_job(job.id, "manual")
    assert failed.status is ScheduledJobStatus.FAILED
    assert failed.error_message == "manual"


def test_scheduler_job_not_found(scheduler: SchedulerService) -> None:
    with pytest.raises(ScheduledJobNotFoundError):
        scheduler.run_job(uuid.uuid4())
