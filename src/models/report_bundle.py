"""Report bundle model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ReportBundle(Base, TimestampMixin):
    """A named bundle of report requests generated together."""

    __tablename__ = "report_bundles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bundle_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    def __repr__(self) -> str:
        return (
            f"ReportBundle(id={self.id!r}, bundle_name={self.bundle_name!r}, "
            f"created_at={self.created_at!r})"
        )
