"""Tests for the :class:`TemplateContext` value object."""

from __future__ import annotations

from src.value_objects import TemplateContext


def test_empty_context_defaults() -> None:
    context = TemplateContext()
    assert context.as_dict() == {}
    assert context.get("missing") is None
    assert context.get("missing", "fallback") == "fallback"


def test_as_dict_returns_copy() -> None:
    context = TemplateContext({"a": 1})
    snapshot = context.as_dict()
    snapshot["a"] = 99
    assert context.get("a") == 1


def test_with_value_is_immutable() -> None:
    context = TemplateContext({"a": 1})
    extended = context.with_value("b", 2)
    assert "b" not in context
    assert "b" in extended
    assert extended.get("a") == 1
    assert extended.get("b") == 2


def test_contains() -> None:
    context = TemplateContext({"a": 1})
    assert "a" in context
    assert "z" not in context


def test_equality_and_repr() -> None:
    a = TemplateContext({"a": 1})
    b = TemplateContext({"a": 1})
    c = TemplateContext({"a": 2})
    assert a == b
    assert a != c
    assert a.__eq__("not-a-context") is NotImplemented
    assert "TemplateContext(" in repr(a)
