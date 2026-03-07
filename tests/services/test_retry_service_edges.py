"""Edge-case tests for retry execution, backoff, and event recording."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from src.models import DomainEventType, RetryStrategy, ScheduledJobStatus
from src.services import (
    BackoffService,
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
    job = scheduler.create_job("   ", _at())
    scheduler.run_job(job.id)
    return job


def test_exponential_backoff_matrix() -> None:
    backoff = BackoffService()
    base = 2
    expected = {1: 2, 2: 4, 3: 8, 4: 16, 5: 32}
    for attempt, value in expected.items():
        assert (
            backoff.calculate_delay(RetryStrategy.EXPONENTIAL, base, attempt)
            == value
        )


def test_next_retry_at_reflects_linear_delay(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.LINEAR, max_attempts=3, base_delay_seconds=10)

    before = datetime.now(timezone.utc)
    attempt = retry.retry_job(job.id, config)
    after = datetime.now(timezone.utc)

    # attempt 1 -> linear delay = base * 1 = 10s
    assert attempt.next_retry_at is not None
    assert attempt.next_retry_at >= before + timedelta(seconds=10)
    assert attempt.next_retry_at <= after + timedelta(seconds=10)


def test_immediate_strategy_sets_zero_delay_next_retry(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.IMMEDIATE, max_attempts=3, base_delay_seconds=99)

    before = datetime.now(timezone.utc)
    attempt = retry.retry_job(job.id, config)
    after = datetime.now(timezone.utc)

    # IMMEDIATE -> 0 delay, so next_retry_at is essentially "now".
    assert before <= attempt.next_retry_at <= after + timedelta(seconds=1)


def test_failed_then_recovered_sequence(
    scheduler: SchedulerService,
    retry: RetryService,
    events: EventService,
) -> None:
    # First attempt fails (blank name). Then fix the name so the next succeeds.
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.LINEAR, max_attempts=5, base_delay_seconds=1)

    first = retry.retry_job(job.id, config)
    assert first.successful is False

    job.job_name = "fixed"  # the underlying cause is resolved
    second = retry.retry_job(job.id, config)
    assert second.successful is True
    assert second.next_retry_at is None
    assert job.status is ScheduledJobStatus.COMPLETED

    assert len(events.get_events_by_type(DomainEventType.RETRY_FAILED)) == 1
    assert len(events.get_events_by_type(DomainEventType.RETRY_SUCCEEDED)) == 1


def test_exhaustion_does_not_record_extra_attempt(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.IMMEDIATE, max_attempts=1, base_delay_seconds=0)

    retry.retry_job(job.id, config)
    assert len(retry.get_attempts(job.id)) == 1

    with pytest.raises(RetryExhaustedError):
        retry.retry_job(job.id, config)
    # No extra attempt recorded by the failed call.
    assert len(retry.get_attempts(job.id)) == 1


def test_attempts_isolated_between_jobs(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job_a = _failing_job(scheduler)
    job_b = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.IMMEDIATE, max_attempts=3, base_delay_seconds=0)

    retry.retry_job(job_a.id, config)
    retry.retry_job(job_a.id, config)
    retry.retry_job(job_b.id, config)

    assert len(retry.get_attempts(job_a.id)) == 2
    assert len(retry.get_attempts(job_b.id)) == 1


def test_single_attempt_max_failure_has_no_next_retry(
    scheduler: SchedulerService, retry: RetryService
) -> None:
    job = _failing_job(scheduler)
    config = RetryConfig(RetryStrategy.LINEAR, max_attempts=1, base_delay_seconds=5)

    attempt = retry.retry_job(job.id, config)
    assert attempt.successful is False
    # attempt_number (1) == max_attempts (1) -> no further retry scheduled
    assert attempt.next_retry_at is None
