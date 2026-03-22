"""Tests for notification category, template, and preference models."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    NotificationCategory,
    NotificationPreference,
    NotificationTemplate,
)


def _category(session: Session, name: str = "orders") -> NotificationCategory:
    category = NotificationCategory(name=name, description="Order events")
    session.add(category)
    session.flush()
    return category


def test_create_category(session: Session) -> None:
    category = _category(session)
    assert isinstance(category.id, uuid.UUID)
    assert category.templates == []
    assert category.preferences == []


def test_category_name_unique(session: Session) -> None:
    _category(session, name="dup")
    session.add(NotificationCategory(name="dup"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_template_belongs_to_category(session: Session) -> None:
    category = _category(session)
    template = NotificationTemplate(
        name="order_confirmed",
        subject_template="Order {ref}",
        body_template="Your order {ref} is confirmed.",
        category=category,
    )
    session.add(template)
    session.flush()

    assert template.category is category
    assert template in category.templates


def test_template_name_unique(session: Session) -> None:
    category = _category(session)
    session.add(
        NotificationTemplate(
            name="dup",
            subject_template="s",
            body_template="b",
            category_id=category.id,
        )
    )
    session.flush()
    session.add(
        NotificationTemplate(
            name="dup",
            subject_template="s",
            body_template="b",
            category_id=category.id,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_preference_defaults_enabled(session: Session) -> None:
    category = _category(session)
    pref = NotificationPreference(category_id=category.id)
    session.add(pref)
    session.flush()

    assert pref.enabled is True
    assert pref.category is category


def test_preference_unique_per_category(session: Session) -> None:
    category = _category(session)
    session.add(NotificationPreference(category_id=category.id))
    session.flush()
    session.add(NotificationPreference(category_id=category.id))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_deleting_category_cascades(session: Session) -> None:
    category = _category(session)
    session.add(
        NotificationTemplate(
            name="t",
            subject_template="s",
            body_template="b",
            category_id=category.id,
        )
    )
    session.add(NotificationPreference(category_id=category.id))
    session.flush()

    session.delete(category)
    session.flush()
    assert session.query(NotificationTemplate).count() == 0
    assert session.query(NotificationPreference).count() == 0
