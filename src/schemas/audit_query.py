"""Audit query schema."""

from __future__ import annotations

from typing import NamedTuple


class AuditQuery(NamedTuple):
    """Optional filters for querying audit entries.

    Both fields are optional; when neither is set, the query matches all
    entries.
    """

    entity_type: str | None = None
    action: str | None = None
