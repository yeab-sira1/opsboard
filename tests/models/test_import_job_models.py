"""Tests for the :class:`ImportJob` model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import ImportJob, ImportJobStatus


def test_create_import_job_defaults(session: Session) -> None:
    job = ImportJob(source_name="upload.csv")
    session.add(job)
    session.flush()

    assert isinstance(job.id, uuid.UUID)
    assert job.status is ImportJobStatus.PENDING
    assert job.row_count == 0
    assert job.error_message is None
    assert isinstance(job.created_at, datetime)


def test_import_job_records_outcome(session: Session) -> None:
    job = ImportJob(
        source_name="upload.csv",
        row_count=3,
        status=ImportJobStatus.FAILED,
        error_message="Unknown product",
    )
    session.add(job)
    session.flush()

    assert job.row_count == 3
    assert job.status is ImportJobStatus.FAILED
    assert job.error_message == "Unknown product"
