"""Generic repository providing common persistence operations."""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Common CRUD operations for a single ORM model.

    Concrete repositories subclass this and bind a specific model type,
    sharing one :class:`~sqlalchemy.orm.Session` per unit of work.
    """

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    def add(self, entity: ModelT) -> ModelT:
        """Stage ``entity`` for insertion and flush to assign defaults."""
        self._session.add(entity)
        self._session.flush()
        return entity

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        """Return the entity with ``entity_id`` or ``None`` if absent."""
        return self._session.get(self._model, entity_id)

    def list(self) -> list[ModelT]:
        """Return all entities of the bound model type."""
        return list(self._session.scalars(select(self._model)).all())

    def delete(self, entity: ModelT) -> None:
        """Remove ``entity`` and flush the deletion."""
        self._session.delete(entity)
        self._session.flush()
