"""Repository for :class:`RetryPolicy` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.retry_policy import RetryPolicy
from src.repositories.base_repository import BaseRepository


class RetryPolicyRepository(BaseRepository[RetryPolicy]):
    """CRUD operations and lookups for retry policies."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, RetryPolicy)

    def get_by_name(self, name: str) -> RetryPolicy | None:
        """Return the policy with the given name, or ``None`` if absent."""
        stmt = select(RetryPolicy).where(RetryPolicy.name == name)
        return self._session.scalars(stmt).first()
