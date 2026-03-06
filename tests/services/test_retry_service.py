"""Tests for :class:`RetryService`."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from src.models import DomainEventType, RetryStrategy, ScheduledJobStatus
from src.services import (
    EventService,
    RetryExhaustedError,
    RetryService,
    SchedulerService,
)
from src.value_objects import RetryConfig


def _at() -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def scheduler(session: Session) -> SchedulerService:
    return SchedulerService(session)


@pytest.fixture
def events(session: Session) -> EventService:
    return EventService(session)


@pytest.fixture
def retry(session: Session) -> RetryService:
    return RetryService(session)


def _failing_job(scheduler: SchedulerService):
    """A blank job_name makes the scheduler run fail deterministically."""
    job = scheduler.create_job("   ", _at())
    scheduler.run_job(job.id)
    assert job.status is ScheduledJobStatus.FAILED
    return job


def _succeeding_job(scheduler: SchedulerService):
    job = scheduler.create_job("nightly", _at())
    scheduler.run_job(job.id)
    assert job.status is ScheduledJobStatus.COMPLETED
    return job


def test_successful_retry_records_successful_attempt(
    scheduler: SchedulerService,
    retry: RetryService,
    events: EventService,
) -> None:
    # Create a job that failed, but will succeed on retry (rename via new job).
    job = scheduler.create_job("nightly", _at())
    scheduler.fail_job(job.id, "transient")

    config = RetryConfig(RetryStrategy.LINEAR, max_attempts=3, base_delay_seconds=5)
    attempt = retry.retry_job(job.id, config)

    assert attempt.successful is True
    assert attempt.attempt_number == 1
    assert attempt.next_retry_at is None
    assert (
        len(events.get_events_by_type(DomainEventType.RETRY_SUCCEEDED)) == 1
    )


def test_failed_retry_records_failed_attempt_with_next_retry(
    scheduler: SchedulerService,
    retry: RetryService,
    events: EventService,
) -> None:
    job = _failing_job(scheduler)

    config = RetryConfig(
        RetryStrategy.EXPONENTIAL, max_attempts=3, base_delay_seconds=10
    )
    attempt = retry.retry_job(job.id, config)

    assert attempt.successful is False
    assert attempt.attempt_number == 1
    assert attempt.next_retry_at is not None  # more attempts remain
    assert len(events.get_events_by_type(DomainEventType.RETRY_FAILED)) == 1


def test_retry_respects_max_attempts(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.IMMEDIATE, max_attempts=2, base_delay_seconds=0)

    retry.retry_job(job.id, config)
    retry.retry_job(job.id, config)

    assert len(retry.get_attempts(job.id)) == 2
    with pytest.raises(RetryExhaustedError):
        retry.retry_job(job.id, config)


def test_last_allowed_attempt_has_no_next_retry(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.LINEAR, max_attempts=2, base_delay_seconds=5)

    retry.retry_job(job.id, config)  # attempt 1, next_retry set
    second = retry.retry_job(job.id, config)  # attempt 2 == max, no next

    assert second.attempt_number == 2
    assert second.next_retry_at is None


def test_get_attempts_returns_in_order(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.IMMEDIATE, max_attempts=3, base_delay_seconds=0)
    retry.retry_job(job.id, config)
    retry.retry_job(job.id, config)

    attempts = retry.get_attempts(job.id)
    assert [a.attempt_number for a in attempts] == [1, 2]
