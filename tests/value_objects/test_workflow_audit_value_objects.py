"""Tests for the AuditContext and WorkflowStep value objects."""

from __future__ import annotations

import pytest

from src.value_objects import AuditContext, WorkflowStep


class TestAuditContext:
    def test_properties(self) -> None:
        context = AuditContext(
            actor="alice", reason="fix", metadata={"ticket": "OPS-1"}
        )
        assert context.actor == "alice"
        assert context.reason == "fix"
        assert context.metadata == {"ticket": "OPS-1"}

    def test_metadata_defaults_to_empty(self) -> None:
        context = AuditContext(actor="alice", reason="fix")
        assert context.metadata == {}

    def test_metadata_is_copied(self) -> None:
        source = {"ticket": "OPS-1"}
        context = AuditContext(actor="alice", reason="fix", metadata=source)
        source["ticket"] = "MUTATED"
        assert context.metadata == {"ticket": "OPS-1"}
        # The returned dict is also a copy.
        context.metadata["ticket"] = "ALSO-MUTATED"
        assert context.metadata == {"ticket": "OPS-1"}

    def test_empty_actor_rejected(self) -> None:
        with pytest.raises(ValueError):
            AuditContext(actor="", reason="fix")

    def test_equality(self) -> None:
        a = AuditContext("alice", "fix", {"k": 1})
        b = AuditContext("alice", "fix", {"k": 1})
        c = AuditContext("bob", "fix", {"k": 1})
        assert a == b
        assert a != c
        assert a.__eq__("not-a-context") is NotImplemented

    def test_repr(self) -> None:
        context = AuditContext("alice", "fix")
        assert "AuditContext(" in repr(context)
        assert "alice" in repr(context)


class TestWorkflowStep:
    def test_properties(self) -> None:
        step = WorkflowStep("import", True, "imported 10 rows")
        assert step.step_name == "import"
        assert step.successful
        assert step.message == "imported 10 rows"

    def test_message_defaults_to_empty(self) -> None:
        step = WorkflowStep("import", False)
        assert step.message == ""

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            WorkflowStep("", True)

    def test_equality(self) -> None:
        a = WorkflowStep("import", True, "ok")
        b = WorkflowStep("import", True, "ok")
        c = WorkflowStep("import", False, "ok")
        assert a == b
        assert a != c
        assert a.__eq__(42) is NotImplemented

    def test_repr(self) -> None:
        step = WorkflowStep("import", True, "ok")
        assert "WorkflowStep(" in repr(step)
        assert "import" in repr(step)
