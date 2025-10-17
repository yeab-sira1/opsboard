"""Report job model: a synchronous execution of a report request."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.report_request import ReportRequest


class ReportJobStatus(enum.Enum):
    """Lifecycle states for a report job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An execution attempt for a :class:`ReportRequest`.

    Records the run status, when it finished, and any error captured while
    generating the report.
    """

    __tablename__ = "report_jobs"

    report_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_requests.id")
    )
    status: Mapped[ReportJobStatus] = mapped_column(
        SAEnum(ReportJobStatus, name="report_job_status"),
        default=ReportJobStatus.PENDING,
    )
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    report_request: Mapped["ReportRequest"] = relationship(
        back_populates="jobs"
    )

    def __repr__(self) -> str:
        return (
            f"ReportJob(id={self.id!r}, status={self.status.name}, "
            f"report_request_id={self.report_request_id!r})"
        )
