"""Repository for :class:`WorkflowExecution` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.workflow_execution import WorkflowExecution, WorkflowStatus
from src.repositories.base_repository import BaseRepository


class WorkflowExecutionRepository(BaseRepository[WorkflowExecution]):
    """CRUD operations and lookups for workflow executions."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkflowExecution)

    def get_by_status(
        self, status: WorkflowStatus
    ) -> list[WorkflowExecution]:
        """Return all workflow executions in the given ``status``."""
        return list(
            self._session.scalars(
                select(WorkflowExecution).where(
                    WorkflowExecution.status == status
                )
            ).all()
        )

    def get_recent(self, limit: int = 10) -> list[WorkflowExecution]:
        """Return the most recently started executions, newest first."""
        return list(
            self._session.scalars(
                select(WorkflowExecution)
                .order_by(WorkflowExecution.started_at.desc())
                .limit(limit)
            ).all()
        )
