"""Tests for :class:`RetryAttemptRepository`."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models import RetryAttempt, ScheduledJob
from src.repositories import RetryAttemptRepository


def _job(session: Session, name: str = "nightly") -> ScheduledJob:
    job = ScheduledJob(
        job_name=name,
        scheduled_for=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session.add(job)
    session.flush()
    return job


def test_get_by_job_orders_by_attempt_number(session: Session) -> None:
    job = _job(session)
    repo = RetryAttemptRepository(session)
    repo.add(RetryAttempt(scheduled_job_id=job.id, attempt_number=2))
    repo.add(RetryAttempt(scheduled_job_id=job.id, attempt_number=1))

    attempts = repo.get_by_job(job.id)
    assert [a.attempt_number for a in attempts] == [1, 2]


def test_get_failed_and_successful_attempts(session: Session) -> None:
    job = _job(session)
    repo = RetryAttemptRepository(session)
    repo.add(
        RetryAttempt(
            scheduled_job_id=job.id, attempt_number=1, successful=False
        )
    )
    repo.add(
        RetryAttempt(
            scheduled_job_id=job.id, attempt_number=2, successful=True
        )
    )

    assert len(repo.get_failed_attempts(job.id)) == 1
    assert len(repo.get_successful_attempts(job.id)) == 1


def test_attempts_are_isolated_per_job(session: Session) -> None:
    job1 = _job(session, "a")
    job2 = _job(session, "b")
    repo = RetryAttemptRepository(session)
    repo.add(RetryAttempt(scheduled_job_id=job1.id, attempt_number=1))

    assert len(repo.get_by_job(job1.id)) == 1
    assert repo.get_by_job(job2.id) == []
