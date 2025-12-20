"""Import job model: a record of a bulk CSV import attempt."""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ImportJobStatus(enum.Enum):
    """Lifecycle states for a bulk import."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An attempt to import data from a named CSV source.

    Records how many rows the source contained and the final outcome; on
    failure the captured ``error_message`` explains why nothing was applied.
    """

    __tablename__ = "import_jobs"

    source_name: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[ImportJobStatus] = mapped_column(
        SAEnum(ImportJobStatus, name="import_job_status"),
        default=ImportJobStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    def __repr__(self) -> str:
        return (
            f"ImportJob(id={self.id!r}, source_name={self.source_name!r}, "
            f"status={self.status.name})"
        )
