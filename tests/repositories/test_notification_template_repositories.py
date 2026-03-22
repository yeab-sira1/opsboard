"""Tests for the notification category/template/preference repositories."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.models import (
    NotificationCategory,
    NotificationPreference,
    NotificationTemplate,
)
from src.repositories import (
    NotificationCategoryRepository,
    NotificationPreferenceRepository,
    NotificationTemplateRepository,
)


def _category(session: Session, name: str = "orders") -> NotificationCategory:
    category = NotificationCategory(name=name)
    session.add(category)
    session.flush()
    return category


def test_category_get_by_name(session: Session) -> None:
    repo = NotificationCategoryRepository(session)
    category = repo.add(NotificationCategory(name="orders"))

    assert repo.get_by_name("orders") is category
    assert repo.get_by_name("missing") is None


def test_template_get_by_name(session: Session) -> None:
    category = _category(session)
    repo = NotificationTemplateRepository(session)
    template = repo.add(
        NotificationTemplate(
            name="order_confirmed",
            subject_template="s",
            body_template="b",
            category_id=category.id,
        )
    )

    assert repo.get_by_name("order_confirmed") is template
    assert repo.get_by_name("missing") is None


def test_preference_get_enabled_and_by_category(session: Session) -> None:
    cat1 = _category(session, "orders")
    cat2 = _category(session, "alerts")
    repo = NotificationPreferenceRepository(session)

    enabled = repo.add(NotificationPreference(category_id=cat1.id))
    repo.add(
        NotificationPreference(category_id=cat2.id, enabled=False)
    )

    assert [p.id for p in repo.get_enabled()] == [enabled.id]
    assert repo.get_by_category(cat1.id) is enabled
    assert repo.get_by_category(cat2.id).enabled is False
