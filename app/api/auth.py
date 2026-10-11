from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.auth import TokenRequest, TokenResponse
from app.security.auth import (
    ACCESS_TOKEN_MINUTES,
    authenticate_user,
    create_access_token,
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