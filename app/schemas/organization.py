from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


OrganizationRole = Literal[
    "organization_admin",
    "operations_manager",
    "analyst",
    "viewer",
]


class MemberCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=150)
    role: OrganizationRole
    password: str | None = Field(default=None, min_length=14, max_length=256)

    @field_validator("email", "full_name")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        if value.count("@") != 1 or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
        return value.lower()


class MemberUpdateRequest(BaseModel):
    role: OrganizationRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_a_change(self):
        if self.role is None and self.is_active is None:
            raise ValueError("At least one member field must be provided.")
        return self


class MemberResponse(BaseModel):
    membership_id: int
    user_id: int
    email: str
    full_name: str
    role: OrganizationRole
    is_active: bool
