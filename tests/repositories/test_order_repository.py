"""Tests for :class:`OrderRepository`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.models import Order, OrderStatus
from src.repositories import OrderRepository


def test_get_by_reference(session: Session) -> None:
    repo = OrderRepository(session)
    order = repo.add(Order(reference="ORD-1"))

    assert repo.get_by_reference("ORD-1") is order
    assert repo.get_by_reference("missing") is None


def test_get_by_status(session: Session) -> None:
    repo = OrderRepository(session)
    pending = repo.add(Order(reference="ORD-1"))
    repo.add(Order(reference="ORD-2", status=OrderStatus.CONFIRMED))

    pending_orders = repo.get_by_status(OrderStatus.PENDING)
    assert [o.id for o in pending_orders] == [pending.id]
    assert len(repo.get_by_status(OrderStatus.CONFIRMED)) == 1
    assert repo.get_by_status(OrderStatus.COMPLETED) == []
