"""Audit service: records and queries immutable state-change history."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from src.models.audit_entry import AuditEntry
from src.repositories import AuditEntryRepository
from src.schemas import AuditQuery
from src.value_objects import AuditContext

CREATED_ACTION = "created"
UPDATED_ACTION = "updated"
DELETED_ACTION = "deleted"


class AuditService:
    """Records immutable audit entries and answers audit queries.

    State is captured as opaque JSON snapshots; no diff is computed between the
    old and new states. When an :class:`AuditContext` is supplied, the actor,
    reason, and metadata are folded into the operation's primary snapshot so
    the history records who made the change and why.
    """

    def __init__(self, session: Session) -> None:
        self._entries = AuditEntryRepository(session)

    def record_creation(
        self,
        entity_type: str,
        entity_id: str,
        new_state: Mapping[str, Any],
        *,
        context: AuditContext | None = None,
        workflow_execution_id: uuid.UUID | None = None,
    ) -> AuditEntry:
        """Record that an entity was created with ``new_state``."""
        return self._record(
            entity_type,
            entity_id,
            CREATED_ACTION,
            old_state=None,
            new_state=new_state,
            context=context,
            workflow_execution_id=workflow_execution_id,
        )

    def record_change(
        self,
        entity_type: str,
        entity_id: str,
        old_state: Mapping[str, Any],
        new_state: Mapping[str, Any],
        *,
        context: AuditContext | None = None,
        workflow_execution_id: uuid.UUID | None = None,
    ) -> AuditEntry:
        """Record that an entity changed from ``old_state`` to ``new_state``."""
        return self._record(
            entity_type,
            entity_id,
            UPDATED_ACTION,
            old_state=old_state,
            new_state=new_state,
            context=context,
            workflow_execution_id=workflow_execution_id,
        )

    def record_deletion(
        self,
        entity_type: str,
        entity_id: str,
        old_state: Mapping[str, Any],
        *,
        context: AuditContext | None = None,
        workflow_execution_id: uuid.UUID | None = None,
    ) -> AuditEntry:
        """Record that an entity in ``old_state`` was deleted."""
        return self._record(
            entity_type,
            entity_id,
            DELETED_ACTION,
            old_state=old_state,
            new_state=None,
            context=context,
            workflow_execution_id=workflow_execution_id,
        )

    def query_audit(self, query: AuditQuery) -> list[AuditEntry]:
        """Return audit entries matching ``query``'s optional filters."""
        if query.entity_type is not None and query.action is not None:
            return [
                entry
                for entry in self._entries.get_by_action(query.action)
                if entry.entity_type == query.entity_type
            ]
        if query.entity_type is not None:
            return [
                entry
                for entry in self._entries.list()
                if entry.entity_type == query.entity_type
            ]
        if query.action is not None:
            return self._entries.get_by_action(query.action)
        return self._entries.list()

    def _record(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        *,
        old_state: Mapping[str, Any] | None,
        new_state: Mapping[str, Any] | None,
        context: AuditContext | None,
        workflow_execution_id: uuid.UUID | None,
    ) -> AuditEntry:
        # The primary snapshot of a deletion is the prior state; for creations
        # and changes it is the resulting state. The context rides along on it.
        primary_is_old = new_state is None
        old_json = self._dump(
            old_state, context if primary_is_old else None
        )
        new_json = self._dump(
            new_state, None if primary_is_old else context
        )
        return self._entries.add(
            AuditEntry(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                old_state_json=old_json,
                new_state_json=new_json,
                workflow_execution_id=workflow_execution_id,
            )
        )

    @staticmethod
    def _dump(
        state: Mapping[str, Any] | None, context: AuditContext | None
    ) -> str | None:
        if state is None:
            return None
        payload: dict[str, Any] = dict(state)
        if context is not None:
            payload["_context"] = {
                "actor": context.actor,
                "reason": context.reason,
                "metadata": context.metadata,
            }
        return json.dumps(payload, sort_keys=True, default=str)
