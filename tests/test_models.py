"""Tests for the core ORM models and the base repository."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from src.config.database import (
    create_database_engine,
    create_session_factory,
    init_database,
    session_scope,
)
from src.models import Organization, Role, User
from src.repositories import BaseRepository


def test_create_user_assigns_uuid_and_timestamp(session: Session) -> None:
    user = User(username="alice", email="alice@example.com")
    session.add(user)
    session.flush()

    assert isinstance(user.id, uuid.UUID)
    assert isinstance(user.created_at, datetime)
    assert user.organization_id is None
    assert user.role_id is None


def test_create_organization(session: Session) -> None:
    org = Organization(name="Acme")
    session.add(org)
    session.flush()

    assert isinstance(org.id, uuid.UUID)
    assert isinstance(org.created_at, datetime)
    assert org.users == []


def test_create_role_with_optional_description(session: Session) -> None:
    role = Role(name="operator", description="Handles day-to-day operations")
    session.add(role)
    session.flush()

    assert isinstance(role.id, uuid.UUID)
    assert role.description == "Handles day-to-day operations"

    bare_role = Role(name="viewer")
    session.add(bare_role)
    session.flush()
    assert bare_role.description is None


def test_user_belongs_to_organization(session: Session) -> None:
    org = Organization(name="Globex")
    user = User(username="bob", email="bob@example.com", organization=org)
    session.add(user)
    session.flush()

    assert user.organization is org
    assert user.organization_id == org.id
    assert user in org.users


def test_user_assigned_role(session: Session) -> None:
    role = Role(name="admin")
    user = User(username="carol", email="carol@example.com", role=role)
    session.add(user)
    session.flush()

    assert user.role is role
    assert user in role.users


def test_base_repository_round_trip(session: Session) -> None:
    repo: BaseRepository[Organization] = BaseRepository(session, Organization)

    created = repo.add(Organization(name="Initech"))
    fetched = repo.get(created.id)

    assert fetched is created
    assert [o.id for o in repo.list()] == [created.id]

    repo.delete(created)
    assert repo.get(created.id) is None


def test_session_scope_commits_on_success() -> None:
    engine = create_database_engine()
    init_database(engine)
    factory = create_session_factory(engine)

    with session_scope(factory) as scoped:
        scoped.add(Organization(name="Umbrella"))

    with session_scope(factory) as scoped:
        names = [org.name for org in scoped.query(Organization).all()]
    assert names == ["Umbrella"]
    engine.dispose()


def test_session_scope_rolls_back_on_error() -> None:
    engine = create_database_engine()
    init_database(engine)
    factory = create_session_factory(engine)

    with pytest.raises(ValueError):
        with session_scope(factory) as scoped:
            scoped.add(Organization(name="Soylent"))
            raise ValueError("boom")

    with session_scope(factory) as scoped:
        assert scoped.query(Organization).count() == 0
    engine.dispose()
