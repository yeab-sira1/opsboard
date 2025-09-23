"""Tests for :class:`ReportRequestRepository`."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models import ReportRequest, ReportType
from src.repositories import ReportRequestRepository


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def test_get_by_report_type(session: Session) -> None:
    repo = ReportRequestRepository(session)
    repo.add(ReportRequest(report_type=ReportType.INVENTORY_SUMMARY))
    repo.add(ReportRequest(report_type=ReportType.INVENTORY_SUMMARY))
    repo.add(ReportRequest(report_type=ReportType.ORDER_SUMMARY))

    assert len(repo.get_by_report_type(ReportType.INVENTORY_SUMMARY)) == 2
    assert len(repo.get_by_report_type(ReportType.ORDER_SUMMARY)) == 1
    assert repo.get_by_report_type(ReportType.DAILY_SNAPSHOT) == []


def test_get_recent_orders_newest_first_and_limits(session: Session) -> None:
    repo = ReportRequestRepository(session)
    oldest = repo.add(
        ReportRequest(
            report_type=ReportType.INVENTORY_SUMMARY, requested_at=_at(1)
        )
    )
    middle = repo.add(
        ReportRequest(
            report_type=ReportType.ORDER_SUMMARY, requested_at=_at(2)
        )
    )
    newest = repo.add(
        ReportRequest(
            report_type=ReportType.RESERVATION_SUMMARY, requested_at=_at(3)
        )
    )

    recent = repo.get_recent(limit=2)
    assert [r.id for r in recent] == [newest.id, middle.id]
    assert oldest.id not in {r.id for r in recent}

    all_recent = repo.get_recent()
    assert [r.id for r in all_recent] == [newest.id, middle.id, oldest.id]
