"""Root application exception."""

from __future__ import annotations


class OpsboardError(Exception):
    """Root exception for all opsboard application errors.

    Catching :class:`OpsboardError` at a boundary will catch every domain,
    service, and application exception raised by this library while leaving
    standard Python exceptions (``ValueError``, ``TypeError``, etc.) to
    propagate normally.
    """
