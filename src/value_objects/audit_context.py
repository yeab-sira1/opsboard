"""Audit context value object."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class AuditContext:
    """Immutable context describing who made a change and why.

    ``metadata`` holds arbitrary supplementary key/value pairs; it is copied on
    construction so the context cannot be mutated through the original mapping.
    """

    def __init__(
        self,
        actor: str,
        reason: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not actor:
            raise ValueError("actor must not be empty")
        self._actor = actor
        self._reason = reason
        self._metadata: dict[str, Any] = dict(metadata or {})

    @property
    def actor(self) -> str:
        """The actor responsible for the change."""
        return self._actor

    @property
    def reason(self) -> str:
        """The reason the change was made."""
        return self._reason

    @property
    def metadata(self) -> dict[str, Any]:
        """A copy of the supplementary metadata."""
        return dict(self._metadata)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AuditContext):
            return NotImplemented
        return (
            self._actor == other._actor
            and self._reason == other._reason
            and self._metadata == other._metadata
        )

    def __repr__(self) -> str:
        return (
            f"AuditContext(actor={self._actor!r}, "
            f"reason={self._reason!r}, metadata={self._metadata!r})"
        )
