"""Edge-case tests for :class:`ReportJobService` execution."""

from __future__ import annotations

import json
import uuid
from datetime import date

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
    InvalidReportJobStateError,
    InventoryService,
    NotificationService,
    ReportJobService,
    ReservationService,
)


@pytest.fixture
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def reservations(session: Session) -> ReservationService:
    return ReservationService(session)


@pytest.fixture
def analytics(session: Session) -> AnalyticsService:
    return AnalyticsService(session)


@pytest.fixture
def notifications(session: Session) -> NotificationService:
    return NotificationService(session)


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


@pytest.mark.parametrize(
    "report_type",
    [
        ReportType.INVENTORY_SUMMARY,
        ReportType.ORDER_SUMMARY,
        ReportType.RESERVATION_SUMMARY,
    ],
)
def test_run_job_completes_for_each_simple_report_type(
    session: Session,
    jobs: ReportJobService,
    report_type: ReportType,
) -> None:
    request_id = _request(session, report_type)
    job = jobs.create_job(request_id)

    run = jobs.run_job(job.id)
    assert run.status is ReportJobStatus.COMPLETED


def test_run_snapshot_job_success(
    session: Session,
    inventory: InventoryService,
    reservations: ReservationService,
    analytics: AnalyticsService,
    jobs: ReportJobService,
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)
    reservations.create_reservation(product.id, warehouse.id, 4, "A")
    analytics.generate_daily_snapshot(date(2026, 1, 1))

    request_id = _request(
        session, ReportType.DAILY_SNAPSHOT, snapshot_date="2026-01-01"
    )
    job = jobs.create_job(request_id)

    run = jobs.run_job(job.id)
    assert run.status is ReportJobStatus.COMPLETED
    assert run.error_message is None


def test_failed_run_keeps_completed_at_and_one_notification(
    session: Session,
    jobs: ReportJobService,
    notifications: NotificationService,
) -> None:
    # Malformed snapshot_date -> failure inside _produce.
    request_id = _request(
        session, ReportType.DAILY_SNAPSHOT, snapshot_date="not-a-date"
    )
    job = jobs.create_job(request_id)

    run = jobs.run_job(job.id)
    assert run.status is ReportJobStatus.FAILED
    assert run.completed_at is not None
    assert (
        len(notifications.get_notifications_by_status(NotificationStatus.PENDING))
        == 1
    )


def test_cannot_fail_completed_job(
    session: Session, jobs: ReportJobService
) -> None:
    request_id = _request(session, ReportType.ORDER_SUMMARY)
    job = jobs.create_job(request_id)
    jobs.run_job(job.id)

    with pytest.raises(InvalidReportJobStateError):
        jobs.fail_job(job.id, "too late")


def test_get_jobs_by_status(
    session: Session, jobs: ReportJobService
) -> None:
    r1 = _request(session, ReportType.ORDER_SUMMARY)
    r2 = _request(session, ReportType.ORDER_SUMMARY)
    completed = jobs.create_job(r1)
    jobs.run_job(completed.id)
    pending = jobs.create_job(r2)

    assert [j.id for j in jobs.get_jobs_by_status(ReportJobStatus.PENDING)] == [
        pending.id
    ]
    assert [
        j.id for j in jobs.get_jobs_by_status(ReportJobStatus.COMPLETED)
    ] == [completed.id]


def test_each_run_creates_its_own_job_record(
    session: Session, jobs: ReportJobService
) -> None:
    request_id = _request(session, ReportType.ORDER_SUMMARY)
    first = jobs.create_job(request_id)
    second = jobs.create_job(request_id)
    jobs.run_job(first.id)
    jobs.run_job(second.id)

    assert first.id != second.id
    assert (
        len(jobs.get_jobs_by_status(ReportJobStatus.COMPLETED)) == 2
    )
