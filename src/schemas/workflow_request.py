"""Workflow request schema."""

from __future__ import annotations

from typing import NamedTuple


class WorkflowRequest(NamedTuple):
    """A request to run a named workflow."""

    workflow_name: str
    send_notifications: bool = False
