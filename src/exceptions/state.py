"""State-related exceptions for opsboard."""

from __future__ import annotations

from src.exceptions.base import OpsboardError


class ConflictError(OpsboardError):
    """Raised when an operation would violate a uniqueness or conflict rule.

    Examples: duplicate order reference, snapshot already exists for a date.
    """


class InvalidStateError(OpsboardError):
    """Raised when an operation is invalid for an entity's current state.

    Examples: completing a PENDING order, releasing an already-released
    reservation, running a non-PENDING scheduled job.
    """
