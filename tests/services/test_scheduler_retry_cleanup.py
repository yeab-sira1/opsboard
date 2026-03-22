"""Tests for SchedulerService.get_job / reset_for_retry and retry consistency."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from src.models import ScheduledJobStatus
from src.services import (
    RetryService,
    SchedulerService,
    ScheduledJobNotFoundError,
)
from src.value_objects import RetryConfig
from src.models import RetryStrategy


def _at() -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def scheduler(session: Session) -> SchedulerService:
    return SchedulerService(session)


@pytest.fixture
def retry(session: Session) -> RetryService:
    return RetryService(session)


def test_get_job_returns_job(scheduler: SchedulerService) -> None:
    job = scheduler.create_job("nightly", _at())
    assert scheduler.get_job(job.id) is job


def test_get_job_missing_raises(scheduler: SchedulerService) -> None:
    with pytest.raises(ScheduledJobNotFoundError):
        scheduler.get_job(uuid.uuid4())


def test_reset_for_retry_clears_failed_state(
    scheduler: SchedulerService,
) -> None:
    job = scheduler.create_job("nightly", _at())
    scheduler.fail_job(job.id, "boom")
    assert job.status is ScheduledJobStatus.FAILED

    reset = scheduler.reset_for_retry(job.id)
    assert reset.status is ScheduledJobStatus.PENDING
    assert reset.completed_at is None
    assert reset.error_message is None


def test_reset_for_retry_noop_on_pending(
    scheduler: SchedulerService,
) -> None:
    job = scheduler.create_job("nightly", _at())
    reset = scheduler.reset_for_retry(job.id)
    assert reset is job
    assert reset.status is ScheduledJobStatus.PENDING


def test_retry_uses_public_scheduler_api(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    # End-to-end: a failed job retried successfully via the refactored path.
    job = scheduler.create_job("nightly", _at())
    scheduler.fail_job(job.id, "transient")

    config = RetryConfig(RetryStrategy.LINEAR, max_attempts=3, base_delay_seconds=5)
    attempt = retry.retry_job(job.id, config)

    assert attempt.successful is True
    assert job.status is ScheduledJobStatus.COMPLETED
