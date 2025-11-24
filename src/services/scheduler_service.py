"""Scheduler service: synchronous execution of scheduled jobs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.base import utcnow
from src.models.domain_event import DomainEventType
from src.models.notification import NotificationStatus
from src.models.report_job import ReportJobStatus
from src.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from src.repositories import ScheduledJobRepository
from src.services.event_service import EventService
from src.services.notification_service import NotificationService
from src.services.report_job_service import ReportJobService


class SchedulerError(Exception):
    """Base class for scheduler-related errors."""


class ScheduledJobNotFoundError(SchedulerError):
    """Raised when a referenced scheduled job does not exist."""

    def __init__(self, job_id: uuid.UUID) -> None:
        super().__init__(f"Scheduled job not found: {job_id}")
        self.job_id = job_id


class InvalidScheduledJobStateError(SchedulerError):
    """Raised when an operation is invalid for the job's current status."""

    def __init__(self, job_id: uuid.UUID, status: ScheduledJobStatus) -> None:
        super().__init__(
            f"Invalid scheduled job state for operation: job={job_id}, "
            f"status={status.name}"
        )
        self.job_id = job_id
        self.status = status


class SchedulerExecutionError(SchedulerError):
    """Raised inside a job run to signal a recoverable execution failure."""


class SchedulerService:
    """Runs scheduled jobs synchronously and records domain events.

    A run drives pending report jobs to completion (via
    :class:`ReportJobService`) and delivers pending notifications (via
    :class:`NotificationService`), recording a :class:`DomainEvent` for each
    report generated and notification sent. Failures mark the job ``FAILED``
    and capture the error message.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._jobs = ScheduledJobRepository(session)
        self._report_jobs = ReportJobService(session)
        self._notifications = NotificationService(session)
        self._events = EventService(session)

    def create_job(
        self, job_name: str, scheduled_for: datetime
    ) -> ScheduledJob:
        """Create a ``PENDING`` scheduled job."""
        return self._jobs.add(
            ScheduledJob(
                job_name=job_name,
                scheduled_for=scheduled_for,
                status=ScheduledJobStatus.PENDING,
            )
        )

    def run_job(self, job_id: uuid.UUID) -> ScheduledJob:
        """Execute a pending job: PENDING → RUNNING → COMPLETED/FAILED.

        Any error transitions the job to FAILED and records the message rather
        than propagating.
        """
        job = self._require_job(job_id)
        if job.status is not ScheduledJobStatus.PENDING:
            raise InvalidScheduledJobStateError(job.id, job.status)

        job.status = ScheduledJobStatus.RUNNING
        self._session.flush()

        try:
            self._execute(job)
        except Exception as exc:  # noqa: BLE001 - runner records any failure
            job.status = ScheduledJobStatus.FAILED
            job.completed_at = utcnow()
            job.error_message = str(exc)
        else:
            job.status = ScheduledJobStatus.COMPLETED
            job.completed_at = utcnow()
        self._session.flush()
        return job

    def fail_job(
        self, job_id: uuid.UUID, error_message: str
    ) -> ScheduledJob:
        """Manually mark a pending or running job as ``FAILED``."""
        job = self._require_job(job_id)
        if job.status not in (
            ScheduledJobStatus.PENDING,
            ScheduledJobStatus.RUNNING,
        ):
            raise InvalidScheduledJobStateError(job.id, job.status)
        job.status = ScheduledJobStatus.FAILED
        job.completed_at = utcnow()
        job.error_message = error_message
        self._session.flush()
        return job

    def get_jobs_by_status(
        self, status: ScheduledJobStatus
    ) -> list[ScheduledJob]:
        """Return all scheduled jobs in the given ``status``."""
        return self._jobs.get_by_status(status)

    def _execute(self, job: ScheduledJob) -> None:
        """Run pending report jobs and deliver notifications, with events."""
        if not job.job_name.strip():
            raise SchedulerExecutionError("job_name must not be empty")

        for report_job in self._report_jobs.get_jobs_by_status(
            ReportJobStatus.PENDING
        ):
            self._report_jobs.run_job(report_job.id)
            self._events.record_event(
                DomainEventType.REPORT_GENERATED,
                {"report_job_id": str(report_job.id)},
            )

        for notification in self._notifications.get_notifications_by_status(
            NotificationStatus.PENDING
        ):
            self._notifications.mark_sent(notification.id)
            self._events.record_event(
                DomainEventType.NOTIFICATION_SENT,
                {"notification_id": str(notification.id)},
            )

    def _require_job(self, job_id: uuid.UUID) -> ScheduledJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise ScheduledJobNotFoundError(job_id)
        return job
