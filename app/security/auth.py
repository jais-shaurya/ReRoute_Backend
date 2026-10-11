from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    AppUser,
    Customer,
    Factory,
    Organization,
    OrganizationEntityAccess,
    Route,
    Supplier,
    Warehouse,
)


def ensure_organization_entity_access(db: Session, organization_id: int) -> None:
    entity_models = [
        ("supplier", Supplier),
        ("customer", Customer),
        ("warehouse", Warehouse),
        ("factory", Factory),
        ("route", Route),
    ]

    for entity_type, model in entity_models:
        for item in db.query(model).all():
            existing = (
                db.query(OrganizationEntityAccess)
                .filter_by(organization_id=organization_id, entity_type=entity_type, entity_id=item.id)
                .first()
            )
            if existing is None:
                db.add(
                    OrganizationEntityAccess(
                        organization_id=organization_id,
                        entity_type=entity_type,
                        entity_id=item.id,
                    )
                )

    db.commit()


def ensure_bootstrap_user(db: Session) -> AppUser:
    organization = db.query(Organization).filter_by(slug="default").first()
    if organization is None:
        organization = Organization(name="Default Organization", slug="default")
        db.add(organization)
        db.commit()
        db.refresh(organization)

    user = db.query(AppUser).filter_by(email="admin@reroute.local").first()
    if user is None:
        user = AppUser(
            email="admin@reroute.local",
            full_name="System Administrator",
            role="admin",
            organization_id=organization.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    ensure_organization_entity_access(db, organization.id)

    return user


def get_current_user(
    db: Session = Depends(get_db),
    x_organization_id: int | None = Header(None, alias="X-Organization-Id"),
    x_user_id: int | None = Header(None, alias="X-User-Id"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
) -> AppUser:
    if x_user_id is None or x_organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id and X-Organization-Id headers are required.",
        )

    user = (
        db.query(AppUser)
        .filter_by(id=x_user_id, organization_id=x_organization_id, is_active=True)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not authorized for this organization.",
        )

    if x_user_role is not None and x_user_role != user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The supplied role does not match the authenticated user's role.",
        )

    return user


def require_role(*allowed_roles: str):
    def dependency(current_user: AppUser = Depends(get_current_user)) -> AppUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted for this action.",
            )
        return current_user

    return dependency


def require_tenant_scope(
    tenant_id: int,
    current_user: AppUser = Depends(get_current_user),
):
    if current_user.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization mismatch. You cannot access another organization's data.",
        )
    return current_user
