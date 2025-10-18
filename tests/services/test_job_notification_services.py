"""Tests for :class:`NotificationService` and :class:`ReportJobService`."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models import (
    NotificationStatus,
    ReportJobStatus,
    ReportRequest,
    ReportType,
)
from src.services import (
    AnalyticsService,
    InvalidNotificationStateError,
    InvalidReportJobStateError,
    InventoryService,
    NotificationNotFoundError,
    NotificationService,
    ReportJobNotFoundError,
    ReportJobService,
    ReportRequestNotFoundError,
    ReservationService,
)


# --- NotificationService -------------------------------------------------


@pytest.fixture
def notifications(session: Session) -> NotificationService:
    return NotificationService(session)


def test_notification_create_and_mark_sent(
    notifications: NotificationService,
) -> None:
    notification = notifications.create_notification("Subject", "Body")
    assert notification.status is NotificationStatus.PENDING

    sent = notifications.mark_sent(notification.id)
    assert sent.status is NotificationStatus.SENT
    assert isinstance(sent.sent_at, datetime)


def test_notification_mark_failed(
    notifications: NotificationService,
) -> None:
    notification = notifications.create_notification("Subject", "Body")
    failed = notifications.mark_failed(notification.id)
    assert failed.status is NotificationStatus.FAILED
    assert failed.sent_at is None


def test_notification_invalid_transitions(
    notifications: NotificationService,
) -> None:
    notification = notifications.create_notification("Subject", "Body")
    notifications.mark_sent(notification.id)

    with pytest.raises(InvalidNotificationStateError):
        notifications.mark_sent(notification.id)
    with pytest.raises(InvalidNotificationStateError):
        notifications.mark_failed(notification.id)


def test_notification_not_found(
    notifications: NotificationService,
) -> None:
    with pytest.raises(NotificationNotFoundError):
        notifications.mark_sent(uuid.uuid4())


def test_get_notifications_by_status(
    notifications: NotificationService,
) -> None:
    a = notifications.create_notification("a", "1")
    notifications.create_notification("b", "2")
    notifications.mark_sent(a.id)

    assert (
        len(notifications.get_notifications_by_status(NotificationStatus.SENT))
        == 1
    )
    assert (
        len(
            notifications.get_notifications_by_status(
                NotificationStatus.PENDING
            )
        )
        == 1
    )


# --- ReportJobService ----------------------------------------------------


@pytest.fixture
def jobs(session: Session) -> ReportJobService:
    return ReportJobService(session)


def _request(session: Session, report_type: ReportType, **params) -> uuid.UUID:
    request = ReportRequest(
        report_type=report_type,
        parameters_json=json.dumps(params) if params else "{}",
    )
    session.add(request)
    session.flush()
    return request.id


def test_create_job_requires_existing_request(
    jobs: ReportJobService,
) -> None:
    with pytest.raises(ReportRequestNotFoundError):
        jobs.create_job(uuid.uuid4())


def test_run_job_success_creates_notification(
    session: Session,
    jobs: ReportJobService,
    notifications: NotificationService,
) -> None:
    request_id = _request(session, ReportType.INVENTORY_SUMMARY)
    job = jobs.create_job(request_id)

    run = jobs.run_job(job.id)
    assert run.status is ReportJobStatus.COMPLETED
    assert isinstance(run.completed_at, datetime)
    assert run.error_message is None

    pending = notifications.get_notifications_by_status(
        NotificationStatus.PENDING
    )
    assert len(pending) == 1
    assert pending[0].subject == "Report completed: inventory_summary"


def test_run_job_failure_records_error_and_notification(
    session: Session,
    jobs: ReportJobService,
    notifications: NotificationService,
) -> None:
    # DAILY_SNAPSHOT with no snapshot_date parameter -> failure during run.
    request_id = _request(session, ReportType.DAILY_SNAPSHOT)
    job = jobs.create_job(request_id)

    run = jobs.run_job(job.id)
    assert run.status is ReportJobStatus.FAILED
    assert run.error_message is not None

    pending = notifications.get_notifications_by_status(
        NotificationStatus.PENDING
    )
    assert len(pending) == 1
    assert pending[0].subject == "Report failed: daily_snapshot"


def test_run_job_invalid_state(
    session: Session, jobs: ReportJobService
) -> None:
    request_id = _request(session, ReportType.ORDER_SUMMARY)
    job = jobs.create_job(request_id)
    jobs.run_job(job.id)

    with pytest.raises(InvalidReportJobStateError):
        jobs.run_job(job.id)


def test_fail_job(session: Session, jobs: ReportJobService) -> None:
    request_id = _request(session, ReportType.ORDER_SUMMARY)
    job = jobs.create_job(request_id)

    failed = jobs.fail_job(job.id, "manual failure")
    assert failed.status is ReportJobStatus.FAILED
    assert failed.error_message == "manual failure"


def test_job_not_found(jobs: ReportJobService) -> None:
    with pytest.raises(ReportJobNotFoundError):
        jobs.run_job(uuid.uuid4())
