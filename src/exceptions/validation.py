"""Validation exception base for opsboard."""

from __future__ import annotations

from src.exceptions.base import OpsboardError


class ValidationError(OpsboardError):
    """Raised when domain input fails a business rule.

    Examples: negative stock quantity, zero reservation quantity, malformed
    import CSV, non-JSON-serializable cache value.
    """
