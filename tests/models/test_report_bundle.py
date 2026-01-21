"""Tests for report bundle models."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from src.models import ReportBundle


class TestReportBundle:
    def test_create_bundle(self) -> None:
        bundle = ReportBundle(
            id=uuid.uuid4(), bundle_name="Daily Reports"
        )
        assert bundle.bundle_name == "Daily Reports"
        assert bundle.id is not None

    def test_default_id_generation(self, session: Session) -> None:
        bundle = ReportBundle(bundle_name="Weekly Reports")
        session.add(bundle)
        session.flush()
        assert bundle.id is not None
        assert isinstance(bundle.id, uuid.UUID)

    def test_rejects_empty_bundle_name(self) -> None:
        bundle = ReportBundle(bundle_name="")
        assert bundle.bundle_name == ""

    def test_timestamps_set_on_persist(self, session: Session) -> None:
        bundle = ReportBundle(bundle_name="Test Bundle")
        session.add(bundle)
        session.flush()
        assert bundle.created_at is not None

    def test_bundle_name_constraints(self, session: Session) -> None:
        bundle = ReportBundle(
            bundle_name="A" * 255
        )
        session.add(bundle)
        session.flush()
        assert len(bundle.bundle_name) == 255

    def test_repr(self) -> None:
        bundle = ReportBundle(bundle_name="Test")
        repr_str = repr(bundle)
        assert "ReportBundle" in repr_str
        assert "Test" in repr_str
