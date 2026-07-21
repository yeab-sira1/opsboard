"""Not-found exception base for opsboard."""

from __future__ import annotations

from src.exceptions.base import OpsboardError


class NotFoundError(OpsboardError):
    """Raised when a requested entity does not exist.

    All ``*NotFoundError`` classes in individual services inherit from this
    base, so callers can catch any missing-entity error at a single point::

        try:
            ...
        except NotFoundError:
            return http_404(...)
    """
