"""Tests for the report job and notification repositories."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.models import (
    Notification,
    NotificationStatus,
    ReportJob,
    ReportJobStatus,
    ReportRequest,
    ReportType,
)
from src.repositories import NotificationRepository, ReportJobRepository


def test_report_job_repository_status_queries(session: Session) -> None:
    request = ReportRequest(report_type=ReportType.INVENTORY_SUMMARY)
    session.add(request)
    session.flush()
    repo = ReportJobRepository(session)

    pending = repo.add(ReportJob(report_request_id=request.id))
    repo.add(
        ReportJob(
            report_request_id=request.id,
            status=ReportJobStatus.COMPLETED,
        )
    )

    assert [j.id for j in repo.get_pending_jobs()] == [pending.id]
    assert len(repo.get_by_status(ReportJobStatus.COMPLETED)) == 1
    assert repo.get_by_status(ReportJobStatus.FAILED) == []


def test_notification_repository_status_queries(session: Session) -> None:
    repo = NotificationRepository(session)

    pending = repo.add(Notification(subject="a", body="b"))
    repo.add(
        Notification(
            subject="c", body="d", status=NotificationStatus.SENT
        )
    )

    assert [n.id for n in repo.get_pending_notifications()] == [pending.id]
    assert len(repo.get_by_status(NotificationStatus.SENT)) == 1
    assert repo.get_by_status(NotificationStatus.FAILED) == []
