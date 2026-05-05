"""Workflow C: Report request → Report job → Scheduler → Notification → Domain events."""

from __future__ import annotations

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
    NotificationService,
    ReportJobService,
    SchedulerService,
)


# ---------------------------------------------------------------------------
# Test 1 — full report-job lifecycle via ReportJobService
# ---------------------------------------------------------------------------


def test_report_job_full_lifecycle(session: Session) -> None:
    """ReportRequest → pending job → run → COMPLETED + success notification."""
    # Arrange: create an ORDER_SUMMARY report request
    request = ReportRequest(report_type=ReportType.ORDER_SUMMARY)
    session.add(request)
    session.flush()

    report_svc = ReportJobService(session)
    notification_svc = NotificationService(session)

    # Act: create and run the job
    job = report_svc.create_job(request.id)
    report_svc.run_job(job.id)

    # Assert job completed
    assert job.status is ReportJobStatus.COMPLETED
    assert job.completed_at is not None

    # Assert a PENDING success notification was created by run_job
    pending = notification_svc.get_notifications_by_status(NotificationStatus.PENDING)
    assert len(pending) == 1
    assert "order_summary" in pending[0].subject


# ---------------------------------------------------------------------------
# Test 2 — scheduler runs all pending report jobs and records events
# ---------------------------------------------------------------------------


def test_scheduler_runs_pending_report_jobs(session: Session) -> None:
    """Scheduler processes 2 pending report jobs, emits REPORT_GENERATED and NOTIFICATION_SENT events."""
    report_svc = ReportJobService(session)
    scheduler_svc = SchedulerService(session)
    event_svc = EventService(session)

    # Arrange: 2 report requests with matching pending jobs
    req1 = ReportRequest(report_type=ReportType.INVENTORY_SUMMARY)
    req2 = ReportRequest(report_type=ReportType.RESERVATION_SUMMARY)
    session.add_all([req1, req2])
    session.flush()

    job1 = report_svc.create_job(req1.id)
    job2 = report_svc.create_job(req2.id)

    # Arrange: a scheduled job
    sched_job = scheduler_svc.create_job(
        "nightly", datetime(2026, 1, 1, tzinfo=timezone.utc)
    )

    # Act
    scheduler_svc.run_job(sched_job.id)

    # Assert scheduled job completed
    assert sched_job.status is ScheduledJobStatus.COMPLETED

    # Assert both report jobs are now COMPLETED
    assert job1.status is ReportJobStatus.COMPLETED
    assert job2.status is ReportJobStatus.COMPLETED

    # Assert domain events
    report_events = event_svc.get_events_by_type(DomainEventType.REPORT_GENERATED)
    assert len(report_events) == 2

    notif_events = event_svc.get_events_by_type(DomainEventType.NOTIFICATION_SENT)
    assert len(notif_events) == 2


# ---------------------------------------------------------------------------
# Test 3 — scheduler delivers pending notifications
# ---------------------------------------------------------------------------


def test_scheduler_delivers_pending_notifications(session: Session) -> None:
    """Scheduler marks 3 PENDING notifications as SENT and emits NOTIFICATION_SENT events."""
    notification_svc = NotificationService(session)
    scheduler_svc = SchedulerService(session)
    event_svc = EventService(session)

    # Arrange: 3 pending notifications
    notification_svc.create_notification("Alert 1", "body 1")
    notification_svc.create_notification("Alert 2", "body 2")
    notification_svc.create_notification("Alert 3", "body 3")

    sched_job = scheduler_svc.create_job(
        "delivery-run", datetime(2026, 1, 1, tzinfo=timezone.utc)
    )

    # Act
    scheduler_svc.run_job(sched_job.id)

    # Assert all notifications sent
    still_pending = notification_svc.get_notifications_by_status(NotificationStatus.PENDING)
    assert len(still_pending) == 0

    sent = notification_svc.get_notifications_by_status(NotificationStatus.SENT)
    assert len(sent) == 3

    # Assert domain events
    notif_events = event_svc.get_events_by_type(DomainEventType.NOTIFICATION_SENT)
    assert len(notif_events) == 3


# ---------------------------------------------------------------------------
# Test 4 — failed report job creates failure notification
# ---------------------------------------------------------------------------


def test_failed_report_job_creates_failure_notification(session: Session) -> None:
    """DAILY_SNAPSHOT job without snapshot_date parameter fails and emits failure notification."""
    # Arrange: missing snapshot_date causes _produce to raise KeyError
    request = ReportRequest(
        report_type=ReportType.DAILY_SNAPSHOT,
        parameters_json="{}",
    )
    session.add(request)
    session.flush()

    report_svc = ReportJobService(session)
    notification_svc = NotificationService(session)

    job = report_svc.create_job(request.id)

    # Act
    report_svc.run_job(job.id)

    # Assert job failed with a captured error message
    assert job.status is ReportJobStatus.FAILED
    assert job.error_message is not None

    # Assert a PENDING failure notification was created
    pending = notification_svc.get_notifications_by_status(NotificationStatus.PENDING)
    assert len(pending) == 1
    assert "failed" in pending[0].subject.lower()


# ---------------------------------------------------------------------------
# Test 5 — scheduler with mixed work (report jobs + pending notifications)
# ---------------------------------------------------------------------------


def test_scheduler_with_mixed_work_processes_all(session: Session) -> None:
    """Scheduler handles 1 report job and 2 pending notifications; 3 NOTIFICATION_SENT events total."""
    report_svc = ReportJobService(session)
    notification_svc = NotificationService(session)
    scheduler_svc = SchedulerService(session)
    event_svc = EventService(session)

    # Arrange: 1 report request + pending job
    req = ReportRequest(report_type=ReportType.ORDER_SUMMARY)
    session.add(req)
    session.flush()
    report_svc.create_job(req.id)

    # Arrange: 2 pre-existing pending notifications
    notification_svc.create_notification("Pre-existing 1", "body 1")
    notification_svc.create_notification("Pre-existing 2", "body 2")

    sched_job = scheduler_svc.create_job(
        "mixed-run", datetime(2026, 1, 1, tzinfo=timezone.utc)
    )

    # Act
    scheduler_svc.run_job(sched_job.id)

    # Assert scheduled job completed
    assert sched_job.status is ScheduledJobStatus.COMPLETED

    # Assert 1 REPORT_GENERATED event
    report_events = event_svc.get_events_by_type(DomainEventType.REPORT_GENERATED)
    assert len(report_events) == 1

    # The scheduler emits NOTIFICATION_SENT for:
    #   - the 2 pre-existing pending notifications
    #   - the success notification created by run_job for the report job
    # Total = 3
    notif_events = event_svc.get_events_by_type(DomainEventType.NOTIFICATION_SENT)
    assert len(notif_events) == 3
