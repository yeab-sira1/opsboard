"""Tests for report bundle repository."""

from datetime import datetime, timedelta
import uuid

import pytest
from sqlalchemy.orm import Session

from src.models import ReportBundle
from src.repositories.report_bundle_repository import ReportBundleRepository


@pytest.fixture
def bundle_repo(session: Session) -> ReportBundleRepository:
    return ReportBundleRepository(session)


def test_add_bundle(bundle_repo: ReportBundleRepository, session: Session) -> None:
    bundle = ReportBundle(bundle_name="Test Bundle")
    result = bundle_repo.add(bundle)
    assert result.id is not None
    assert result.bundle_name == "Test Bundle"


def test_get_bundle_by_id(
    bundle_repo: ReportBundleRepository, session: Session
) -> None:
    bundle = ReportBundle(bundle_name="Get Test")
    bundle_repo.add(bundle)
    retrieved = bundle_repo.get(bundle.id)
    assert retrieved is not None
    assert retrieved.bundle_name == "Get Test"


def test_get_nonexistent_bundle(
    bundle_repo: ReportBundleRepository,
) -> None:
    result = bundle_repo.get(uuid.uuid4())
    assert result is None


def test_get_by_name(
    bundle_repo: ReportBundleRepository,
) -> None:
    bundle = ReportBundle(bundle_name="Unique Name")
    bundle_repo.add(bundle)
    retrieved = bundle_repo.get_by_name("Unique Name")
    assert retrieved is not None
    assert retrieved.bundle_name == "Unique Name"


def test_get_by_name_not_found(
    bundle_repo: ReportBundleRepository,
) -> None:
    result = bundle_repo.get_by_name("Nonexistent")
    assert result is None


def test_get_recent_empty(bundle_repo: ReportBundleRepository) -> None:
    result = bundle_repo.get_recent()
    assert result == []


def test_get_recent_single(bundle_repo: ReportBundleRepository) -> None:
    bundle = ReportBundle(bundle_name="Recent 1")
    bundle_repo.add(bundle)
    result = bundle_repo.get_recent()
    assert len(result) == 1
    assert result[0].bundle_name == "Recent 1"


def test_get_recent_multiple(bundle_repo: ReportBundleRepository) -> None:
    bundles = [
        ReportBundle(bundle_name=f"Bundle {i}") for i in range(5)
    ]
    for b in bundles:
        bundle_repo.add(b)
    result = bundle_repo.get_recent(limit=5)
    assert len(result) == 5


def test_get_recent_respects_limit(
    bundle_repo: ReportBundleRepository, session: Session
) -> None:
    bundles = [
        ReportBundle(bundle_name=f"Bundle {i}") for i in range(10)
    ]
    for b in bundles:
        bundle_repo.add(b)
    result = bundle_repo.get_recent(limit=3)
    assert len(result) == 3


def test_get_recent_ordered_by_creation(
    bundle_repo: ReportBundleRepository, session: Session
) -> None:
    b1 = ReportBundle(bundle_name="First")
    bundle_repo.add(b1)
    session.flush()
    b2 = ReportBundle(bundle_name="Second")
    bundle_repo.add(b2)
    session.flush()
    result = bundle_repo.get_recent(limit=2)
    names = {r.bundle_name for r in result}
    assert "First" in names
    assert "Second" in names


def test_list_bundles(
    bundle_repo: ReportBundleRepository,
) -> None:
    bundles = [
        ReportBundle(bundle_name=f"Bundle {i}") for i in range(3)
    ]
    for b in bundles:
        bundle_repo.add(b)
    result = bundle_repo.list()
    assert len(result) == 3


def test_list_empty(bundle_repo: ReportBundleRepository) -> None:
    result = bundle_repo.list()
    assert result == []
