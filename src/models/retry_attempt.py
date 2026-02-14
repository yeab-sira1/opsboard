"""Retry attempt model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.scheduled_job import ScheduledJob


class RetryAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single retry of a scheduled job.

    Records which attempt number this was, whether it succeeded, any error it
    produced, and when the next retry should occur (null when no further retry
    is scheduled).
    """

    __tablename__ = "retry_attempts"

    scheduled_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheduled_jobs.id")
    )
    attempt_number: Mapped[int] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    next_retry_at: Mapped[datetime | None] = mapped_column(default=None)
    successful: Mapped[bool] = mapped_column(default=False)

    scheduled_job: Mapped["ScheduledJob"] = relationship(
        back_populates="retry_attempts"
    )

    def __repr__(self) -> str:
        return (
            f"RetryAttempt(id={self.id!r}, "
            f"scheduled_job_id={self.scheduled_job_id!r}, "
            f"attempt_number={self.attempt_number!r}, "
            f"successful={self.successful!r})"
        )
