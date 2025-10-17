"""Report request model: a logged request for a generated report."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from src.models.report_job import ReportJob


class ReportType(enum.Enum):
    """The kinds of report a request can target."""

    INVENTORY_SUMMARY = "inventory_summary"
    ORDER_SUMMARY = "order_summary"
    RESERVATION_SUMMARY = "reservation_summary"
    DAILY_SNAPSHOT = "daily_snapshot"


class ReportRequest(UUIDPrimaryKeyMixin, Base):
    """A record that a report of a given type was requested.

    ``parameters_json`` holds an opaque JSON string of request parameters (for
    example a snapshot date); it is not interpreted at the storage layer.
    """

    __tablename__ = "report_requests"

    report_type: Mapped[ReportType] = mapped_column(
        SAEnum(ReportType, name="report_type")
    )
    requested_at: Mapped[datetime] = mapped_column(default=utcnow)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")

    jobs: Mapped[list["ReportJob"]] = relationship(
        back_populates="report_request",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"ReportRequest(id={self.id!r}, "
            f"report_type={self.report_type.name})"
        )
