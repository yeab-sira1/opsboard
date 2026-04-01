"""Tests for workflow execution and audit entry models."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.models import (
    AuditEntry,
    WorkflowExecution,
    WorkflowStatus,
)
from src.models.base import utcnow


class TestWorkflowExecution:
    def test_defaults(self, session: Session) -> None:
        execution = WorkflowExecution(workflow_name="inventory_reporting")
        session.add(execution)
        session.flush()

        assert execution.id is not None
        assert execution.status is WorkflowStatus.RUNNING
        assert execution.started_at is not None
        assert execution.completed_at is None
        assert execution.error_message is None
        assert execution.audit_entries == []

    def test_completion_fields(self, session: Session) -> None:
        execution = WorkflowExecution(
            workflow_name="snapshot",
            status=WorkflowStatus.COMPLETED,
            completed_at=utcnow(),
        )
        session.add(execution)
        session.flush()

        assert execution.status is WorkflowStatus.COMPLETED
        assert execution.completed_at is not None

    def test_failure_fields(self, session: Session) -> None:
        execution = WorkflowExecution(
            workflow_name="snapshot",
            status=WorkflowStatus.FAILED,
            error_message="boom",
        )
        session.add(execution)
        session.flush()

        assert execution.status is WorkflowStatus.FAILED
        assert execution.error_message == "boom"

    def test_repr(self, session: Session) -> None:
        execution = WorkflowExecution(workflow_name="snapshot")
        session.add(execution)
        session.flush()
        assert "WorkflowExecution(" in repr(execution)
        assert "snapshot" in repr(execution)


class TestAuditEntry:
    def test_defaults(self, session: Session) -> None:
        entry = AuditEntry(
            entity_type="Order",
            entity_id="abc",
            action="created",
        )
        session.add(entry)
        session.flush()

        assert entry.id is not None
        assert entry.old_state_json is None
        assert entry.new_state_json is None
        assert entry.created_at is not None
        assert entry.workflow_execution_id is None
        assert entry.workflow_execution is None

    def test_state_snapshots(self, session: Session) -> None:
        entry = AuditEntry(
            entity_type="Order",
            entity_id="abc",
            action="updated",
            old_state_json='{"status": "PENDING"}',
            new_state_json='{"status": "COMPLETED"}',
        )
        session.add(entry)
        session.flush()

        assert entry.old_state_json == '{"status": "PENDING"}'
        assert entry.new_state_json == '{"status": "COMPLETED"}'

    def test_relationship_to_workflow(self, session: Session) -> None:
        execution = WorkflowExecution(workflow_name="snapshot")
        session.add(execution)
        session.flush()

        entry = AuditEntry(
            entity_type="WorkflowExecution",
            entity_id=str(execution.id),
            action="started",
            workflow_execution=execution,
        )
        session.add(entry)
        session.flush()

        assert entry.workflow_execution_id == execution.id
        assert execution.audit_entries == [entry]

    def test_cascade_delete(self, session: Session) -> None:
        execution = WorkflowExecution(workflow_name="snapshot")
        entry = AuditEntry(
            entity_type="Order",
            entity_id="abc",
            action="created",
            workflow_execution=execution,
        )
        session.add(execution)
        session.add(entry)
        session.flush()

        session.delete(execution)
        session.flush()
        assert session.get(AuditEntry, entry.id) is None

    def test_repr(self, session: Session) -> None:
        entry = AuditEntry(
            entity_type="Order", entity_id="abc", action="created"
        )
        session.add(entry)
        session.flush()
        assert "AuditEntry(" in repr(entry)
        assert "created" in repr(entry)
