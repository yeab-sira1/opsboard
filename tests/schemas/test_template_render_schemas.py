"""Tests for template render schemas."""

from __future__ import annotations

from src.schemas import TemplateRenderRequest, TemplateRenderResult
from src.value_objects import TemplateContext


class TestTemplateRenderRequest:
    def test_carries_name_and_context(self) -> None:
        context = TemplateContext({"name": "Ada"})
        request = TemplateRenderRequest(
            template_name="welcome", context=context
        )
        assert request.template_name == "welcome"
        assert request.context.get("name") == "Ada"

    def test_equality_by_value(self) -> None:
        a = TemplateRenderRequest("welcome", TemplateContext({"x": 1}))
        b = TemplateRenderRequest("welcome", TemplateContext({"x": 1}))
        assert a == b

    def test_empty_context(self) -> None:
        request = TemplateRenderRequest("welcome", TemplateContext())
        assert request.context.as_dict() == {}


class TestTemplateRenderResult:
    def test_complete_when_no_missing_keys(self) -> None:
        result = TemplateRenderResult(
            template_name="welcome", rendered_text="Hi Ada"
        )
        assert result.rendered_text == "Hi Ada"
        assert result.missing_keys == ()
        assert result.complete

    def test_incomplete_when_keys_missing(self) -> None:
        result = TemplateRenderResult(
            template_name="welcome",
            rendered_text="Hi ",
            missing_keys=("name",),
        )
        assert not result.complete
        assert result.missing_keys == ("name",)
