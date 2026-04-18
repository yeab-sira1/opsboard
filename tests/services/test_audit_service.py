"""Tests for :class:`AuditService`."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from src.schemas import AuditQuery
from src.services import AuditService
from src.value_objects import AuditContext


@pytest.fixture
def audit(session: Session) -> AuditService:
    return AuditService(session)


def test_record_creation_stores_new_state_only(audit: AuditService) -> None:
    entry = audit.record_creation("Order", "1", {"status": "PENDING"})
    assert entry.action == "created"
    assert entry.old_state_json is None
    assert json.loads(entry.new_state_json) == {"status": "PENDING"}


def test_record_change_stores_both_states(audit: AuditService) -> None:
    entry = audit.record_change(
        "Order", "1", {"status": "PENDING"}, {"status": "COMPLETED"}
    )
    assert entry.action == "updated"
    assert json.loads(entry.old_state_json) == {"status": "PENDING"}
    assert json.loads(entry.new_state_json) == {"status": "COMPLETED"}


def test_record_deletion_stores_old_state_only(audit: AuditService) -> None:
    entry = audit.record_deletion("Order", "1", {"status": "COMPLETED"})
    assert entry.action == "deleted"
    assert json.loads(entry.old_state_json) == {"status": "COMPLETED"}
    assert entry.new_state_json is None


def test_context_folds_into_primary_snapshot(audit: AuditService) -> None:
    context = AuditContext(
        actor="alice", reason="correction", metadata={"ticket": "OPS-1"}
    )
    created = audit.record_creation(
        "Order", "1", {"status": "PENDING"}, context=context
    )
    payload = json.loads(created.new_state_json)
    assert payload["_context"]["actor"] == "alice"
    assert payload["_context"]["reason"] == "correction"
    assert payload["_context"]["metadata"] == {"ticket": "OPS-1"}

    deleted = audit.record_deletion(
        "Order", "1", {"status": "DONE"}, context=context
    )
    assert json.loads(deleted.old_state_json)["_context"]["actor"] == "alice"


def test_query_by_entity_type(audit: AuditService) -> None:
    audit.record_creation("Order", "1", {})
    audit.record_creation("Product", "2", {})

    results = audit.query_audit(AuditQuery(entity_type="Order"))
    assert [e.entity_type for e in results] == ["Order"]


def test_query_by_action(audit: AuditService) -> None:
    audit.record_creation("Order", "1", {})
    audit.record_deletion("Order", "1", {})

    results = audit.query_audit(AuditQuery(action="deleted"))
    assert [e.action for e in results] == ["deleted"]


def test_query_by_entity_type_and_action(audit: AuditService) -> None:
    audit.record_creation("Order", "1", {})
    audit.record_creation("Product", "2", {})
    audit.record_deletion("Order", "1", {})

    results = audit.query_audit(
        AuditQuery(entity_type="Order", action="created")
    )
    assert len(results) == 1
    assert results[0].entity_type == "Order"
    assert results[0].action == "created"


def test_query_without_filters_returns_all(audit: AuditService) -> None:
    audit.record_creation("Order", "1", {})
    audit.record_creation("Product", "2", {})

    results = audit.query_audit(AuditQuery())
    assert len(results) == 2
