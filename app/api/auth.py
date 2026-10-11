from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import AppUser
from app.schemas.auth import CurrentUserResponse, OrganizationIdentity, TokenRequest, TokenResponse
from app.security.auth import (
    ACCESS_TOKEN_MINUTES,
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse)
def issue_access_token(payload: TokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )


@router.get("/me", response_model=CurrentUserResponse)
def current_user(current_user: AppUser = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        organization=OrganizationIdentity(
            id=current_user.organization.id,
            name=current_user.organization.name,
            slug=current_user.organization.slug,
        ),
    )