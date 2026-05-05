"""Template rendering service.

Resolves :class:`~src.models.NotificationTemplate` records by name, renders
their subject/body strings against a :class:`~src.value_objects.TemplateContext`,
and optionally creates a :class:`~src.models.Notification` via
:class:`NotificationService`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories import (
    NotificationPreferenceRepository,
    NotificationTemplateRepository,
)
from src.schemas.template_render_result import TemplateRenderResult
from src.services.notification_service import NotificationService
from src.models.notification import Notification
from src.value_objects.template_context import TemplateContext


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TemplateRenderingError(Exception):
    """Base class for template rendering errors."""


class TemplateNotFoundError(TemplateRenderingError):
    """Raised when no template with the given name exists."""

    def __init__(self, template_name: str) -> None:
        super().__init__(f"Notification template not found: {template_name!r}")
        self.template_name = template_name


# ---------------------------------------------------------------------------
# Internal safe-format helper
# ---------------------------------------------------------------------------


class _SafeFormatMap(dict):  # type: ignore[type-arg]
    """A dict subclass that records missing keys instead of raising KeyError.

    Used with :meth:`str.format_map` to support partial rendering.
    """

    def __init__(self, values: dict, missing: list[str]) -> None:
        super().__init__(values)
        self._missing = missing

    def __missing__(self, key: str) -> str:  # type: ignore[override]
        self._missing.append(key)
        # Return the placeholder unchanged so the caller can see it.
        return f"{{{key}}}"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class TemplateRenderingService:
    """Renders notification templates and optionally persists notifications.

    Parameters
    ----------
    session:
        The active SQLAlchemy session for all database operations.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._templates = NotificationTemplateRepository(session)
        self._preferences = NotificationPreferenceRepository(session)
        self._notifications = NotificationService(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self, template_name: str, context: TemplateContext
    ) -> TemplateRenderResult:
        """Render the *body* of a named template against *context*.

        Parameters
        ----------
        template_name:
            The unique name of the :class:`~src.models.NotificationTemplate`.
        context:
            Key/value pairs used to fill template placeholders.

        Returns
        -------
        TemplateRenderResult
            Contains the rendered body text and any missing keys.

        Raises
        ------
        TemplateNotFoundError
            If no template with *template_name* exists.
        """
        template = self._templates.get_by_name(template_name)
        if template is None:
            raise TemplateNotFoundError(template_name)

        rendered_body, missing_keys = self._render_string(
            template.body_template, context
        )
        return TemplateRenderResult(
            template_name=template_name,
            rendered_text=rendered_body,
            missing_keys=tuple(missing_keys),
        )

    def create_notification_from_template(
        self, template_name: str, context: TemplateContext
    ) -> Notification | None:
        """Render a template and create a PENDING notification.

        If a :class:`~src.models.NotificationPreference` record exists for
        the template's category and its ``enabled`` flag is ``False``, the
        notification is **not** created and ``None`` is returned.  A missing
        preference record is treated as *enabled*.

        Parameters
        ----------
        template_name:
            The unique name of the :class:`~src.models.NotificationTemplate`.
        context:
            Key/value pairs used to fill template placeholders.

        Returns
        -------
        Notification | None
            The newly created :class:`~src.models.Notification`, or ``None``
            when the category preference is disabled.

        Raises
        ------
        TemplateNotFoundError
            If no template with *template_name* exists.
        """
        template = self._templates.get_by_name(template_name)
        if template is None:
            raise TemplateNotFoundError(template_name)

        # Check category preference — absence means enabled.
        preference = self._preferences.get_by_category(template.category_id)
        if preference is not None and not preference.enabled:
            return None

        rendered_subject, _ = self._render_string(
            template.subject_template, context
        )
        rendered_body, _ = self._render_string(
            template.body_template, context
        )

        return self._notifications.create_notification(
            subject=rendered_subject,
            body=rendered_body,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_string(
        template_str: str, context: TemplateContext
    ) -> tuple[str, list[str]]:
        """Render *template_str* with *context*, collecting missing keys.

        Returns
        -------
        tuple[str, list[str]]
            The rendered string and a list of any placeholder keys that were
            absent from *context*.
        """
        missing: list[str] = []
        safe_map = _SafeFormatMap(context.as_dict(), missing)
        rendered = template_str.format_map(safe_map)
        return rendered, missing
