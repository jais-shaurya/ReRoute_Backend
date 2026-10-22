from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=160)
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OrganizationIdentity(BaseModel):
    id: int
    name: str
    slug: str


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    organization: OrganizationIdentity
