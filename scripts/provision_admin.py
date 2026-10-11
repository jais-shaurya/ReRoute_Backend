from __future__ import annotations

from getpass import getpass

from app.database.connection import SessionLocal
from app.database.models import AppUser, Organization
from app.security.auth import hash_password


def main() -> None:
    organization_slug = input("Organization slug: ").strip().lower()
    organization_name = input("Organization name: ").strip()
    email = input("Administrator email: ").strip().lower()
    full_name = input("Administrator full name: ").strip()
    password = getpass("Administrator password (12+ characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 12 or password != confirmation:
        raise SystemExit("Password must be at least 12 characters and both entries must match.")

    db = SessionLocal()
    try:
        organization = db.query(Organization).filter_by(slug=organization_slug).first()
        if organization is None:
            organization = Organization(name=organization_name, slug=organization_slug)
            db.add(organization)
            db.flush()

        user = db.query(AppUser).filter_by(email=email).first()
        if user is None:
            user = AppUser(
                email=email,
                full_name=full_name,
                role="admin",
                organization_id=organization.id,
                is_active=True,
            )
            db.add(user)
        elif user.organization_id != organization.id:
            raise SystemExit("That account belongs to another organization.")
        user.password_hash = hash_password(password)
        user.role = "admin"
        user.is_active = True
        db.commit()
        print("Administrator provisioned.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()