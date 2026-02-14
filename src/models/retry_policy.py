"""Retry policy model and strategy enum."""

from __future__ import annotations

import enum

from sqlalchemy import CheckConstraint, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RetryStrategy(enum.Enum):
    """Strategy used to space out retry attempts."""

    IMMEDIATE = "IMMEDIATE"
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"


class RetryPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named, reusable configuration governing how a job is retried."""

    __tablename__ = "retry_policies"
    __table_args__ = (
        CheckConstraint(
            "max_attempts >= 1", name="ck_retry_policy_max_attempts_positive"
        ),
        CheckConstraint(
            "base_delay_seconds >= 0",
            name="ck_retry_policy_base_delay_non_negative",
        ),
    )

    name: Mapped[str] = mapped_column(String(128), unique=True)
    strategy: Mapped[RetryStrategy] = mapped_column(
        SAEnum(RetryStrategy, name="retry_strategy")
    )
    max_attempts: Mapped[int] = mapped_column()
    base_delay_seconds: Mapped[int] = mapped_column()

    def __repr__(self) -> str:
        return (
            f"RetryPolicy(id={self.id!r}, name={self.name!r}, "
            f"strategy={self.strategy.name})"
        )
