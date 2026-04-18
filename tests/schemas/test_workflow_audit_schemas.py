"""Tests for workflow and audit schemas."""

from __future__ import annotations

from src.schemas import AuditQuery, WorkflowRequest, WorkflowResult
from src.value_objects import WorkflowStep


class TestWorkflowRequest:
    def test_defaults_no_notifications(self) -> None:
        request = WorkflowRequest("inventory_reporting")
        assert request.workflow_name == "inventory_reporting"
        assert request.send_notifications is False

    def test_notifications_enabled(self) -> None:
        request = WorkflowRequest("snapshot", send_notifications=True)
        assert request.send_notifications is True


class TestWorkflowResult:
    def test_step_count_and_success(self) -> None:
        steps = [
            WorkflowStep("import", True),
            WorkflowStep("export", True),
        ]
        result = WorkflowResult(successful=True, steps=steps)
        assert result.step_count == 2
        assert result.failed_steps() == []

    def test_failed_steps(self) -> None:
        steps = [
            WorkflowStep("import", True),
            WorkflowStep("export", False, "boom"),
        ]
        result = WorkflowResult(successful=False, steps=steps)
        assert result.step_count == 2
        assert [s.step_name for s in result.failed_steps()] == ["export"]

    def test_empty_steps(self) -> None:
        result = WorkflowResult(successful=True, steps=[])
        assert result.step_count == 0
        assert result.failed_steps() == []


class TestAuditQuery:
    def test_defaults_are_none(self) -> None:
        query = AuditQuery()
        assert query.entity_type is None
        assert query.action is None

    def test_filters(self) -> None:
        query = AuditQuery(entity_type="Order", action="created")
        assert query.entity_type == "Order"
        assert query.action == "created"
