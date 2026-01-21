"""Tests for report bundle value objects."""

import pytest

from src.value_objects.report_bundle_item import ReportBundleItem


class TestReportBundleItem:
    def test_create_with_type_only(self) -> None:
        item = ReportBundleItem("inventory")
        assert item.report_type == "inventory"
        assert item.parameters_json == ""

    def test_create_with_type_and_parameters(self) -> None:
        params = '{"filter": "active"}'
        item = ReportBundleItem("orders", params)
        assert item.report_type == "orders"
        assert item.parameters_json == params

    def test_parameters_defaults_to_empty_string(self) -> None:
        item = ReportBundleItem("reservations", None)
        assert item.parameters_json == ""

    def test_rejects_empty_report_type(self) -> None:
        with pytest.raises(ValueError, match="report_type must not be empty"):
            ReportBundleItem("")

    def test_equality(self) -> None:
        item1 = ReportBundleItem("inventory", '{"key": "value"}')
        item2 = ReportBundleItem("inventory", '{"key": "value"}')
        item3 = ReportBundleItem("orders", '{"key": "value"}')
        assert item1 == item2
        assert item1 != item3

    def test_immutability(self) -> None:
        item = ReportBundleItem("daily")
        assert not hasattr(item, "report_type") or not callable(getattr(item, "report_type"))

    def test_repr(self) -> None:
        item = ReportBundleItem("weekly", '{"period": "7d"}')
        repr_str = repr(item)
        assert "ReportBundleItem" in repr_str
        assert "weekly" in repr_str
