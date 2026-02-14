"""Tests for the retry policy and retry attempt models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    RetryAttempt,
    RetryPolicy,
    RetryStrategy,
    ScheduledJob,
)


def _scheduled_job(session: Session) -> ScheduledJob:
    job = ScheduledJob(
        job_name="nightly",
        scheduled_for=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session.add(job)
    session.flush()
    return job


def test_create_retry_policy(session: Session) -> None:
    policy = RetryPolicy(
        name="default",
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=3,
        base_delay_seconds=5,
    )
    session.add(policy)
    session.flush()

    assert isinstance(policy.id, uuid.UUID)
    assert policy.strategy is RetryStrategy.EXPONENTIAL
    assert isinstance(policy.created_at, datetime)


def test_retry_policy_name_unique(session: Session) -> None:
    session.add(
        RetryPolicy(
            name="dup",
            strategy=RetryStrategy.LINEAR,
            max_attempts=2,
            base_delay_seconds=1,
        )
    )
    session.flush()
    session.add(
        RetryPolicy(
            name="dup",
            strategy=RetryStrategy.LINEAR,
            max_attempts=2,
            base_delay_seconds=1,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_retry_policy_max_attempts_constraint(session: Session) -> None:
    session.add(
        RetryPolicy(
            name="bad",
            strategy=RetryStrategy.IMMEDIATE,
            max_attempts=0,
            base_delay_seconds=1,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_retry_attempt_relationship(session: Session) -> None:
    job = _scheduled_job(session)
    attempt = RetryAttempt(
        scheduled_job=job,
        attempt_number=1,
        error_message="boom",
    )
    session.add(attempt)
    session.flush()

    assert attempt.scheduled_job is job
    assert attempt in job.retry_attempts
    assert attempt.successful is False
    assert attempt.next_retry_at is None


def test_deleting_job_cascades_to_attempts(session: Session) -> None:
    job = _scheduled_job(session)
    session.add(
        RetryAttempt(scheduled_job_id=job.id, attempt_number=1)
    )
    session.flush()
    assert session.query(RetryAttempt).count() == 1

    session.delete(job)
    session.flush()
    assert session.query(RetryAttempt).count() == 0
