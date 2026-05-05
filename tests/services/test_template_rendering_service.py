"""Integration tests for :class:`TemplateRenderingService`."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.models.notification import NotificationStatus
from src.models.notification_category import NotificationCategory
from src.models.notification_preference import NotificationPreference
from src.models.notification_template import NotificationTemplate
from src.services.template_rendering_service import (
    TemplateNotFoundError,
    TemplateRenderingService,
)
from src.value_objects.template_context import TemplateContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_category(session: Session, name: str = "alerts") -> NotificationCategory:
    """Persist and return a :class:`NotificationCategory`."""
    category = NotificationCategory(name=name)
    session.add(category)
    session.flush()
    return category


def _make_template(
    session: Session,
    category: NotificationCategory,
    name: str = "welcome",
    subject: str = "Hello {user}",
    body: str = "Dear {user}, welcome to {org}.",
) -> NotificationTemplate:
    """Persist and return a :class:`NotificationTemplate`."""
    template = NotificationTemplate(
        name=name,
        subject_template=subject,
        body_template=body,
        category_id=category.id,
    )
    session.add(template)
    session.flush()
    return template


def _make_preference(
    session: Session,
    category: NotificationCategory,
    *,
    enabled: bool,
) -> NotificationPreference:
    """Persist and return a :class:`NotificationPreference`."""
    pref = NotificationPreference(category_id=category.id, enabled=enabled)
    session.add(pref)
    session.flush()
    return pref


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_known_template_with_full_context(session: Session) -> None:
    """Rendering a template whose every placeholder is supplied yields a
    complete result with no missing keys."""
    category = _make_category(session)
    _make_template(session, category)

    svc = TemplateRenderingService(session)
    context = TemplateContext({"user": "Alice", "org": "Acme"})

    result = svc.render("welcome", context)

    assert result.template_name == "welcome"
    assert result.rendered_text == "Dear Alice, welcome to Acme."
    assert result.missing_keys == ()
    assert result.complete is True


def test_render_with_missing_keys_returns_them(session: Session) -> None:
    """When the context is missing keys the result captures them and
    ``complete`` is ``False``."""
    category = _make_category(session)
    _make_template(session, category, body="Hi {user}, your ref is {ref}.")

    svc = TemplateRenderingService(session)
    # Only supply 'user'; 'ref' is absent.
    context = TemplateContext({"user": "Bob"})

    result = svc.render("welcome", context)

    assert "ref" in result.missing_keys
    assert result.complete is False
    # The placeholder is kept verbatim in the rendered text.
    assert "{ref}" in result.rendered_text


def test_render_unknown_template_raises(session: Session) -> None:
    """Requesting a non-existent template name raises
    :class:`TemplateNotFoundError`."""
    svc = TemplateRenderingService(session)

    with pytest.raises(TemplateNotFoundError) as exc_info:
        svc.render("does_not_exist", TemplateContext())

    assert "does_not_exist" in str(exc_info.value)


def test_create_notification_from_template_stores_notification(
    session: Session,
) -> None:
    """``create_notification_from_template`` creates a PENDING notification
    whose subject and body come from the rendered template."""
    category = _make_category(session)
    _make_template(
        session,
        category,
        subject="Order {order_id} shipped",
        body="Your order {order_id} has been dispatched.",
    )

    svc = TemplateRenderingService(session)
    context = TemplateContext({"order_id": "ORD-42"})

    notification = svc.create_notification_from_template("welcome", context)

    assert notification is not None
    assert notification.status is NotificationStatus.PENDING
    assert notification.subject == "Order ORD-42 shipped"
    assert notification.body == "Your order ORD-42 has been dispatched."


def test_render_respects_disabled_preference(session: Session) -> None:
    """When the category preference is disabled ``create_notification_from_template``
    returns ``None`` and no notification is stored."""
    from src.repositories import NotificationRepository

    category = _make_category(session)
    _make_template(session, category)
    _make_preference(session, category, enabled=False)

    svc = TemplateRenderingService(session)
    context = TemplateContext({"user": "Carol", "org": "Corp"})

    result = svc.create_notification_from_template("welcome", context)

    assert result is None

    # Confirm nothing was persisted.
    repo = NotificationRepository(session)
    assert repo.list() == []


def test_render_proceeds_without_preference_record(session: Session) -> None:
    """When there is no preference row for the category the notification is
    created (treat absence as enabled)."""
    category = _make_category(session)
    _make_template(session, category)
    # No preference row is inserted.

    svc = TemplateRenderingService(session)
    context = TemplateContext({"user": "Dave", "org": "DevCo"})

    notification = svc.create_notification_from_template("welcome", context)

    assert notification is not None
    assert notification.status is NotificationStatus.PENDING
