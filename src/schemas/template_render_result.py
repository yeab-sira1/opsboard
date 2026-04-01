"""Template render result schema."""

from __future__ import annotations

from typing import NamedTuple


class TemplateRenderResult(NamedTuple):
    """The outcome of rendering a named template."""

    template_name: str
    rendered_text: str
    missing_keys: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """Whether every referenced key was supplied by the context."""
        return not self.missing_keys
