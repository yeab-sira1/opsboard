"""Template context value object."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class TemplateContext:
    """An immutable set of key/value pairs for rendering a template."""

    def __init__(self, values: Mapping[str, Any] | None = None) -> None:
        self._values: dict[str, Any] = dict(values or {})

    def as_dict(self) -> dict[str, Any]:
        """Return a copy of the context values."""
        return dict(self._values)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for ``key`` or ``default`` if absent."""
        return self._values.get(key, default)

    def with_value(self, key: str, value: Any) -> "TemplateContext":
        """Return a new context with ``key`` set to ``value``."""
        updated = dict(self._values)
        updated[key] = value
        return TemplateContext(updated)

    def __contains__(self, key: object) -> bool:
        return key in self._values

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TemplateContext):
            return NotImplemented
        return self._values == other._values

    def __repr__(self) -> str:
        return f"TemplateContext({self._values!r})"
