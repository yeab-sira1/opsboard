"""Tests for the report job and notification models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import (
    Notification,
    NotificationStatus,
    ReportJob,
    ReportJobStatus,
    ReportRequest,
    ReportType,
)


def _report_request(session: Session) -> ReportRequest:
    request = ReportRequest(report_type=ReportType.INVENTORY_SUMMARY)
    session.add(request)
    session.flush()
    return request


def test_create_report_job_defaults(session: Session) -> None:
    request = _report_request(session)
    job = ReportJob(report_request_id=request.id)
    session.add(job)
    session.flush()

    assert isinstance(job.id, uuid.UUID)
    assert job.status is ReportJobStatus.PENDING
    assert isinstance(job.created_at, datetime)
    assert job.completed_at is None
    assert job.error_message is None


def test_report_job_relationship(session: Session) -> None:
    request = _report_request(session)
    job = ReportJob(report_request=request)
    session.add(job)
    session.flush()

    assert job.report_request is request
    assert job in request.jobs


def test_deleting_request_cascades_to_jobs(session: Session) -> None:
    request = _report_request(session)
    session.add(ReportJob(report_request_id=request.id))
    session.flush()
    assert session.query(ReportJob).count() == 1

    session.delete(request)
    session.flush()
    assert session.query(ReportJob).count() == 0


def test_create_notification_defaults(session: Session) -> None:
    notification = Notification(subject="Hello", body="World")
    session.add(notification)
    session.flush()

    assert isinstance(notification.id, uuid.UUID)
    assert notification.status is NotificationStatus.PENDING
    assert notification.sent_at is None
    assert isinstance(notification.created_at, datetime)
