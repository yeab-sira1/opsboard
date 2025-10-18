"""Report job service: synchronous execution of report requests."""

from __future__ import annotations

import json
import uuid
from datetime import date

from sqlalchemy.orm import Session

from src.models.base import utcnow
from src.models.report_job import ReportJob, ReportJobStatus
from src.models.report_request import ReportRequest, ReportType
from src.repositories import ReportJobRepository, ReportRequestRepository
from src.services.dashboard_service import DashboardService
from src.services.export_service import ExportService
from src.services.notification_service import NotificationService


class ReportJobError(Exception):
    """Base class for report-job-related errors."""


class ReportJobNotFoundError(ReportJobError):
    """Raised when a referenced job does not exist."""

    def __init__(self, job_id: uuid.UUID) -> None:
        super().__init__(f"Report job not found: {job_id}")
        self.job_id = job_id


class ReportRequestNotFoundError(ReportJobError):
    """Raised when a job is created for a missing report request."""

    def __init__(self, report_request_id: uuid.UUID) -> None:
        super().__init__(f"Report request not found: {report_request_id}")
        self.report_request_id = report_request_id


class InvalidReportJobStateError(ReportJobError):
    """Raised when an operation is invalid for the job's current status."""

    def __init__(self, job_id: uuid.UUID, status: ReportJobStatus) -> None:
        super().__init__(
            f"Invalid report job state for operation: job={job_id}, "
            f"status={status.name}"
        )
        self.job_id = job_id
        self.status = status


class ReportJobService:
    """Runs report requests synchronously and emits notifications.

    Report content is produced by reusing :class:`ExportService` (the CSV
    artifact) and :class:`DashboardService` (a human summary); aggregation is
    never reimplemented here. Each run emits a success or failure notification.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._jobs = ReportJobRepository(session)
        self._requests = ReportRequestRepository(session)
        self._dashboard = DashboardService(session)
        self._export = ExportService(session)
        self._notifications = NotificationService(session)

    def create_job(self, report_request_id: uuid.UUID) -> ReportJob:
        """Create a ``PENDING`` job for an existing report request."""
        if self._requests.get(report_request_id) is None:
            raise ReportRequestNotFoundError(report_request_id)
        return self._jobs.add(
            ReportJob(
                report_request_id=report_request_id,
                status=ReportJobStatus.PENDING,
            )
        )

    def run_job(self, job_id: uuid.UUID) -> ReportJob:
        """Execute a pending job: PENDING → RUNNING → COMPLETED/FAILED.

        On success the report is generated and a success notification created.
        Any error transitions the job to FAILED and creates a failure
        notification; the error is captured on the job rather than raised.
        """
        job = self._require_job(job_id)
        if job.status is not ReportJobStatus.PENDING:
            raise InvalidReportJobStateError(job.id, job.status)

        job.status = ReportJobStatus.RUNNING
        self._session.flush()

        request = job.report_request
        try:
            output, summary = self._produce(request)
        except Exception as exc:  # noqa: BLE001 - job runner records any failure
            job.status = ReportJobStatus.FAILED
            job.completed_at = utcnow()
            job.error_message = str(exc)
            self._notifications.create_notification(
                subject=f"Report failed: {request.report_type.value}",
                body=str(exc),
            )
        else:
            job.status = ReportJobStatus.COMPLETED
            job.completed_at = utcnow()
            self._notifications.create_notification(
                subject=f"Report completed: {request.report_type.value}",
                body=f"{summary} ({len(output)} bytes)",
            )
        self._session.flush()
        return job

    def fail_job(
        self, job_id: uuid.UUID, error_message: str
    ) -> ReportJob:
        """Manually mark a pending or running job as ``FAILED``."""
        job = self._require_job(job_id)
        if job.status not in (
            ReportJobStatus.PENDING,
            ReportJobStatus.RUNNING,
        ):
            raise InvalidReportJobStateError(job.id, job.status)
        job.status = ReportJobStatus.FAILED
        job.completed_at = utcnow()
        job.error_message = error_message
        self._session.flush()
        return job

    def get_jobs_by_status(
        self, status: ReportJobStatus
    ) -> list[ReportJob]:
        """Return all jobs in the given ``status``."""
        return self._jobs.get_by_status(status)

    def _produce(self, request: ReportRequest) -> tuple[str, str]:
        """Return ``(csv_output, human_summary)`` for a report request."""
        report_type = request.report_type
        if report_type is ReportType.INVENTORY_SUMMARY:
            view = self._dashboard.get_inventory_dashboard()
            return (
                self._export.export_inventory_summary_csv(),
                f"Inventory report: {len(view.rows)} rows, "
                f"{view.total_available} available",
            )
        if report_type is ReportType.ORDER_SUMMARY:
            view = self._dashboard.get_order_dashboard()
            return (
                self._export.export_order_summary_csv(),
                f"Order report: {view.total_orders} orders",
            )
        if report_type is ReportType.RESERVATION_SUMMARY:
            view = self._dashboard.get_reservation_dashboard()
            return (
                self._export.export_reservation_summary_csv(),
                f"Reservation report: {view.total_reservations} reservations",
            )
        # ReportType.DAILY_SNAPSHOT
        params = json.loads(request.parameters_json)
        snapshot_date = date.fromisoformat(params["snapshot_date"])
        view = self._dashboard.get_snapshot_dashboard(snapshot_date)
        return (
            self._export.export_daily_snapshot_csv(snapshot_date),
            f"Snapshot report: {len(view.rows)} rows for {snapshot_date}",
        )

    def _require_job(self, job_id: uuid.UUID) -> ReportJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise ReportJobNotFoundError(job_id)
        return job
