"""Tests for the :class:`ReportRequest` model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import ReportRequest, ReportType


def test_create_report_request_defaults(session: Session) -> None:
    request = ReportRequest(report_type=ReportType.INVENTORY_SUMMARY)
    session.add(request)
    session.flush()

    assert isinstance(request.id, uuid.UUID)
    assert request.report_type is ReportType.INVENTORY_SUMMARY
    assert isinstance(request.requested_at, datetime)
    assert request.parameters_json == "{}"


def test_parameters_json_is_stored(session: Session) -> None:
    request = ReportRequest(
        report_type=ReportType.DAILY_SNAPSHOT,
        parameters_json='{"snapshot_date": "2026-01-01"}',
    )
    session.add(request)
    session.flush()

    assert request.parameters_json == '{"snapshot_date": "2026-01-01"}'


def test_all_report_types_are_persistable(session: Session) -> None:
    for report_type in ReportType:
        session.add(ReportRequest(report_type=report_type))
    session.flush()

    assert session.query(ReportRequest).count() == len(ReportType)
