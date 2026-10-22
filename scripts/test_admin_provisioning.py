import builtins
import getpass

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import Base
from app.database.models import (
    IndustryProfile,
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    User,
)
from app.security.auth import verify_password
from scripts import create_admin


def test_initial_admin_can_be_added_to_migrated_legacy_organization(
    tmp_path,
    monkeypatch,
    capsys,
):
    engine = create_engine(
        "sqlite:///" + (tmp_path / "admin.sqlite3").as_posix()
    )
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(create_admin, "SessionLocal", test_session_factory)

    with Session(engine) as session:
        profile = IndustryProfile(
            code="manufacturing",
            name="Manufacturing",
            version=1,
        )
        session.add(profile)
        session.add(
            Organization(name="Legacy Organization", slug="legacy")
        )
        session.commit()

    answers = iter(
        [
            "Legacy Organization",
            "legacy",
            "admin@example.test",
            "Initial Admin",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))
    passwords = iter(["long-test-password-value", "long-test-password-value"])
    monkeypatch.setattr(getpass, "getpass", lambda _: next(passwords))

    create_admin.create_initial_admin()

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Organization)) == 1
        user = session.scalar(
            select(User).where(User.email == "admin@example.test")
        )
        assert user is not None
        assert verify_password("long-test-password-value", user.password_hash)
        membership = session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id
            )
        )
        assert membership is not None
        assert membership.role == "organization_admin"
        settings = session.scalar(
            select(OrganizationSettings).where(
                OrganizationSettings.organization_id == membership.organization_id
            )
        )
        assert settings is not None

    assert "long-test-password-value" not in capsys.readouterr().out

    answers = iter(
        [
            "Legacy Organization",
            "legacy",
            "second-admin@example.test",
            "Second Admin",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))
    passwords = iter(["another-long-test-password", "another-long-test-password"])
    monkeypatch.setattr(getpass, "getpass", lambda _: next(passwords))

    with pytest.raises(ValueError, match="already has an active administrator"):
        create_admin.create_initial_admin()

    engine.dispose()
