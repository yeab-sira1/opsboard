"""Edge-case tests for :class:`SchedulerService` execution."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from src.models import (
    DomainEventType,
    ReportJobStatus,
    ReportRequest,
    ReportType,
    ScheduledJobStatus,
)
from src.services import (
    EventService,
    InvalidScheduledJobStateError,
    ReportJobService,
    SchedulerService,
)


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


@pytest.fixture
def events(session: Session) -> EventService:
    return EventService(session)


@pytest.fixture
def scheduler(session: Session) -> SchedulerService:
    return SchedulerService(session)


def _pending_report_jobs(session: Session, count: int) -> None:
    report_jobs = ReportJobService(session)
    for _ in range(count):
        request = ReportRequest(report_type=ReportType.ORDER_SUMMARY)
        session.add(request)
        session.flush()
        report_jobs.create_job(request.id)


def test_run_processes_multiple_report_jobs(
    session: Session, scheduler: SchedulerService, events: EventService
) -> None:
    _pending_report_jobs(session, 3)

    job = scheduler.create_job("nightly", _at(1))
    scheduler.run_job(job.id)

    assert (
        len(events.get_events_by_type(DomainEventType.REPORT_GENERATED)) == 3
    )
    assert (
        len(events.get_events_by_type(DomainEventType.NOTIFICATION_SENT)) == 3
    )
    report_jobs = ReportJobService(session)
    assert len(report_jobs.get_jobs_by_status(ReportJobStatus.COMPLETED)) == 3


def test_run_with_no_pending_work_still_completes(
    scheduler: SchedulerService, events: EventService
) -> None:
    job = scheduler.create_job("nightly", _at(1))
    run = scheduler.run_job(job.id)

    assert run.status is ScheduledJobStatus.COMPLETED
    assert events.get_recent_events() == []


def test_cannot_fail_completed_scheduled_job(
    scheduler: SchedulerService,
) -> None:
    job = scheduler.create_job("nightly", _at(1))
    scheduler.run_job(job.id)

    with pytest.raises(InvalidScheduledJobStateError):
        scheduler.fail_job(job.id, "too late")


def test_get_jobs_by_status(scheduler: SchedulerService) -> None:
    completed = scheduler.create_job("a", _at(1))
    scheduler.run_job(completed.id)
    pending = scheduler.create_job("b", _at(2))

    assert [
        j.id for j in scheduler.get_jobs_by_status(ScheduledJobStatus.PENDING)
    ] == [pending.id]
    assert [
        j.id
        for j in scheduler.get_jobs_by_status(ScheduledJobStatus.COMPLETED)
    ] == [completed.id]


def test_recent_events_are_limited_and_ordered(
    session: Session, scheduler: SchedulerService, events: EventService
) -> None:
    _pending_report_jobs(session, 5)
    job = scheduler.create_job("nightly", _at(1))
    scheduler.run_job(job.id)

    # 5 REPORT_GENERATED + 5 NOTIFICATION_SENT events recorded.
    assert len(events.get_recent_events(limit=4)) == 4
    assert len(events.get_recent_events(limit=100)) == 10


def test_failed_run_does_not_mark_completed(
    scheduler: SchedulerService,
) -> None:
    job = scheduler.create_job("", _at(1))
    run = scheduler.run_job(job.id)

    assert run.status is ScheduledJobStatus.FAILED
    assert scheduler.get_jobs_by_status(ScheduledJobStatus.COMPLETED) == []
