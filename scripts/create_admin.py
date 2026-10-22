import getpass
import re

from sqlalchemy import select

from app.database.connection import SessionLocal
from app.database.models import (
    IndustryProfile,
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    User,
)
from app.security.auth import hash_password


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def create_initial_admin() -> None:
    organization_name = input("Organization name: ").strip()
    organization_slug = input("Organization slug: ").strip().lower()
    email = input("Administrator email: ").strip().lower()
    full_name = input("Administrator name: ").strip()
    password = getpass.getpass("Administrator password (14+ characters): ")
    password_confirmation = getpass.getpass("Confirm password: ")

    if not organization_name or not full_name:
        raise ValueError("Organization and administrator names are required.")
    if not SLUG_PATTERN.fullmatch(organization_slug):
        raise ValueError("Use a lowercase slug with letters, numbers, and hyphens.")
    if "@" not in email or len(email) > 320:
        raise ValueError("Enter a valid email address.")
    if len(password) < 14:
        raise ValueError("The password must contain at least 14 characters.")
    if password != password_confirmation:
        raise ValueError("The passwords do not match.")

    with SessionLocal.begin() as session:
        organization = session.scalar(
            select(Organization).where(Organization.slug == organization_slug)
        )
        existing_user = session.scalar(
            select(User).where(User.email == email)
        )
        if existing_user is not None:
            raise ValueError(
                "The administrator email is already in use."
            )

        if organization is None:
            organization = Organization(
                name=organization_name,
                slug=organization_slug,
            )
            session.add(organization)
            session.flush()
        else:
            active_administrators = session.scalar(
                select(OrganizationMembership.id).where(
                    OrganizationMembership.organization_id == organization.id,
                    OrganizationMembership.role == "organization_admin",
                    OrganizationMembership.is_active.is_(True),
                ).limit(1)
            )
            if active_administrators is not None:
                raise ValueError(
                    "This organization already has an active administrator."
                )

        settings = session.scalar(
            select(OrganizationSettings).where(
                OrganizationSettings.organization_id == organization.id
            )
        )
        if settings is None:
            profile = session.scalar(
                select(IndustryProfile)
                .where(
                    IndustryProfile.code == "manufacturing",
                    IndustryProfile.is_active.is_(True),
                )
                .order_by(IndustryProfile.version.desc())
                .limit(1)
            )
            if profile is None:
                raise ValueError(
                    "Industry templates are not initialized; run database migrations first."
                )
            session.add(
                OrganizationSettings(
                    organization_id=organization.id,
                    profile_id=profile.id,
                )
            )

        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
        )
        session.add(user)
        session.flush()
        session.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                role="organization_admin",
            )
        )

    print(
        f"Created organization '{organization_slug}' and its initial administrator."
    )


if __name__ == "__main__":
    create_initial_admin()
