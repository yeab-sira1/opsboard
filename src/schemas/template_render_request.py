"""Template render request schema."""

from __future__ import annotations

from typing import NamedTuple

from src.value_objects import TemplateContext


class TemplateRenderRequest(NamedTuple):
    """A request to render a named template with a context."""

    template_name: str
    context: TemplateContext
