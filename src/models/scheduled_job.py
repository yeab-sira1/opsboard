"""Scheduled job model: a synchronously executed scheduled task."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ScheduledJobStatus(enum.Enum):
    """Lifecycle states for a scheduled job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScheduledJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A task scheduled to run at or after ``scheduled_for``.

    Execution is synchronous; the status, completion time, and any error are
    recorded as the job runs.
    """

    __tablename__ = "scheduled_jobs"

    job_name: Mapped[str] = mapped_column(String(128))
    scheduled_for: Mapped[datetime] = mapped_column()
    status: Mapped[ScheduledJobStatus] = mapped_column(
        SAEnum(ScheduledJobStatus, name="scheduled_job_status"),
        default=ScheduledJobStatus.PENDING,
    )
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    def __repr__(self) -> str:
        return (
            f"ScheduledJob(id={self.id!r}, job_name={self.job_name!r}, "
            f"status={self.status.name})"
        )
