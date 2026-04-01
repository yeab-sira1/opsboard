"""Workflow execution model: a synchronously run, audited workflow."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from src.models.audit_entry import AuditEntry


class WorkflowStatus(enum.Enum):
    """Lifecycle states for a workflow execution."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One synchronous run of a named workflow.

    Execution is synchronous; the status, completion time, and any error are
    recorded as the workflow runs. A run may produce many audit entries.
    """

    __tablename__ = "workflow_executions"

    workflow_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[WorkflowStatus] = mapped_column(
        SAEnum(WorkflowStatus, name="workflow_status"),
        default=WorkflowStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    audit_entries: Mapped[list["AuditEntry"]] = relationship(
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"WorkflowExecution(id={self.id!r}, "
            f"workflow_name={self.workflow_name!r}, "
            f"status={self.status.name})"
        )
