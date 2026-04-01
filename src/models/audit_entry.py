"""Audit entry model: an immutable record of a state change."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from src.models.workflow_execution import WorkflowExecution


class AuditEntry(UUIDPrimaryKeyMixin, Base):
    """An immutable record that an entity changed state.

    ``old_state_json`` and ``new_state_json`` carry opaque JSON snapshots of
    the entity before and after the change; they are not interpreted at the
    storage layer. Either may be null (a creation has no prior state, a
    deletion has no resulting state). An entry may optionally belong to the
    workflow execution that produced it.
    """

    __tablename__ = "audit_entries"

    entity_type: Mapped[str] = mapped_column(String(128))
    entity_id: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    old_state_json: Mapped[str | None] = mapped_column(Text, default=None)
    new_state_json: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("workflow_executions.id"), default=None
    )

    workflow_execution: Mapped["WorkflowExecution | None"] = relationship(
        back_populates="audit_entries"
    )

    def __repr__(self) -> str:
        return (
            f"AuditEntry(id={self.id!r}, entity_type={self.entity_type!r}, "
            f"entity_id={self.entity_id!r}, action={self.action!r})"
        )
