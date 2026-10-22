from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    Organization,
    OrganizationMembership,
    User,
)
from app.schemas.organization import (
    MemberCreateRequest,
    MemberResponse,
    MemberUpdateRequest,
)
from app.security.auth import AuthPrincipal, hash_password
from app.security.permissions import Permission, require_permission


router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


def _require_current_organization(
    organization_id: int,
    principal: AuthPrincipal,
) -> None:
    if principal.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )


def _member_response(
    membership: OrganizationMembership,
    user: User,
) -> MemberResponse:
    return MemberResponse(
        membership_id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        is_active=membership.is_active and user.is_active,
    )


@router.get("/{organization_id}/members", response_model=list[MemberResponse])
def list_members(
    organization_id: int,
    principal: AuthPrincipal = Depends(
        require_permission(Permission.MEMBERS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> list[MemberResponse]:
    _require_current_organization(organization_id, principal)
    rows = (
        db.query(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .filter(OrganizationMembership.organization_id == organization_id)
        .order_by(User.email)
        .all()
    )
    return [
        _member_response(membership, user)
        for membership, user in rows
    ]


@router.post(
    "/{organization_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_member(
    organization_id: int,
    request: MemberCreateRequest,
    principal: AuthPrincipal = Depends(
        require_permission(Permission.MEMBERS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> MemberResponse:
    _require_current_organization(organization_id, principal)
    organization = db.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    user = (
        db.query(User)
        .filter(User.email == request.email)
        .one_or_none()
    )
    if user is None:
        if request.password is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A password is required when creating a new user.",
            )
        user = User(
            email=request.email,
            full_name=request.full_name,
            password_hash=hash_password(request.password),
        )
        db.add(user)
        db.flush()

    existing_membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
        .one_or_none()
    )
    if existing_membership is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization.",
        )

    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.id,
        role=request.role,
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user or membership with these details already exists.",
        ) from None
    db.refresh(membership)
    return _member_response(membership, user)


@router.patch(
    "/{organization_id}/members/{membership_id}",
    response_model=MemberResponse,
)
def update_member(
    organization_id: int,
    membership_id: int,
    request: MemberUpdateRequest,
    principal: AuthPrincipal = Depends(
        require_permission(Permission.MEMBERS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> MemberResponse:
    _require_current_organization(organization_id, principal)
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization member not found.",
        )

    removing_admin = membership.role == "organization_admin" and (
        (request.role is not None and request.role != "organization_admin")
        or request.is_active is False
    )
    if removing_admin:
        active_admin_count = (
            db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == "organization_admin",
                OrganizationMembership.is_active.is_(True),
            )
            .count()
        )
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The last active organization administrator cannot be removed.",
            )

    if request.role is not None:
        membership.role = request.role
    if request.is_active is not None:
        membership.is_active = request.is_active

    db.commit()
    user = db.get(User, membership.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization member not found.",
        )
    return _member_response(membership, user)
