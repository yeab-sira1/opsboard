"""Tests for workflow execution and audit entry repositories."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.models import AuditEntry, WorkflowExecution, WorkflowStatus
from src.models.base import utcnow
from src.repositories import (
    AuditEntryRepository,
    WorkflowExecutionRepository,
)


@pytest.fixture
def workflows(session: Session) -> WorkflowExecutionRepository:
    return WorkflowExecutionRepository(session)


@pytest.fixture
def audit(session: Session) -> AuditEntryRepository:
    return AuditEntryRepository(session)


class TestWorkflowExecutionRepository:
    def test_add_and_get(
        self, workflows: WorkflowExecutionRepository
    ) -> None:
        execution = workflows.add(
            WorkflowExecution(workflow_name="snapshot")
        )
        assert workflows.get(execution.id) is execution

    def test_get_by_status(
        self, workflows: WorkflowExecutionRepository
    ) -> None:
        workflows.add(
            WorkflowExecution(
                workflow_name="a", status=WorkflowStatus.COMPLETED
            )
        )
        workflows.add(
            WorkflowExecution(
                workflow_name="b", status=WorkflowStatus.FAILED
            )
        )
        workflows.add(
            WorkflowExecution(
                workflow_name="c", status=WorkflowStatus.COMPLETED
            )
        )

        completed = workflows.get_by_status(WorkflowStatus.COMPLETED)
        assert {e.workflow_name for e in completed} == {"a", "c"}
        failed = workflows.get_by_status(WorkflowStatus.FAILED)
        assert [e.workflow_name for e in failed] == ["b"]

    def test_get_recent_orders_newest_first(
        self, workflows: WorkflowExecutionRepository
    ) -> None:
        base = utcnow()
        for index, name in enumerate(["old", "mid", "new"]):
            workflows.add(
                WorkflowExecution(
                    workflow_name=name,
                    started_at=base.replace(microsecond=index),
                )
            )

        recent = workflows.get_recent(limit=2)
        assert [e.workflow_name for e in recent] == ["new", "mid"]

    def test_get_recent_empty(
        self, workflows: WorkflowExecutionRepository
    ) -> None:
        assert workflows.get_recent() == []


class TestAuditEntryRepository:
    def _entry(self, **kwargs: object) -> AuditEntry:
        defaults = {
            "entity_type": "Order",
            "entity_id": "1",
            "action": "created",
        }
        defaults.update(kwargs)
        return AuditEntry(**defaults)

    def test_get_by_entity(self, audit: AuditEntryRepository) -> None:
        audit.add(self._entry(entity_id="1", action="created"))
        audit.add(self._entry(entity_id="1", action="updated"))
        audit.add(self._entry(entity_id="2", action="created"))

        entries = audit.get_by_entity("Order", "1")
        assert [e.action for e in entries] == ["created", "updated"]

    def test_get_by_entity_distinguishes_type(
        self, audit: AuditEntryRepository
    ) -> None:
        audit.add(self._entry(entity_type="Order", entity_id="1"))
        audit.add(self._entry(entity_type="Product", entity_id="1"))

        assert len(audit.get_by_entity("Order", "1")) == 1
        assert len(audit.get_by_entity("Product", "1")) == 1

    def test_get_by_action(self, audit: AuditEntryRepository) -> None:
        audit.add(self._entry(action="created"))
        audit.add(self._entry(action="deleted"))
        audit.add(self._entry(action="created"))

        created = audit.get_by_action("created")
        assert len(created) == 2
        assert all(e.action == "created" for e in created)

    def test_get_recent_orders_newest_first(
        self, audit: AuditEntryRepository
    ) -> None:
        base = utcnow()
        for index, action in enumerate(["first", "second", "third"]):
            audit.add(
                self._entry(
                    action=action,
                    created_at=base.replace(microsecond=index),
                )
            )

        recent = audit.get_recent(limit=2)
        assert [e.action for e in recent] == ["third", "second"]

    def test_get_recent_empty(self, audit: AuditEntryRepository) -> None:
        assert audit.get_recent() == []
