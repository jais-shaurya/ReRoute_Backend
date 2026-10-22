from enum import StrEnum

from fastapi import Depends, HTTPException, status

from app.database.models import AppUser
from app.security.auth import get_current_user


class Permission(StrEnum):
    PLANNER_RUN = "planner:run"
    PLANNER_READ = "planner:read"
    SUPPLY_CHAIN_READ = "supply_chain:read"
    SUPPLY_CHAIN_MANAGE = "supply_chain:manage"
    ORGANIZATION_MANAGE = "organization:manage"
    MEMBERS_MANAGE = "members:manage"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "admin": frozenset(Permission),
    "organization_admin": frozenset(Permission),
    "operations_manager": frozenset(
        {
            Permission.PLANNER_RUN,
            Permission.PLANNER_READ,
            Permission.SUPPLY_CHAIN_READ,
            Permission.SUPPLY_CHAIN_MANAGE,
        }
    ),
    "analyst": frozenset(
        {
            Permission.PLANNER_RUN,
            Permission.PLANNER_READ,
            Permission.SUPPLY_CHAIN_READ,
        }
    ),
    "planner": frozenset(
        {
            Permission.PLANNER_RUN,
            Permission.PLANNER_READ,
            Permission.SUPPLY_CHAIN_READ,
        }
    ),
    "viewer": frozenset(
        {
            Permission.PLANNER_READ,
            Permission.SUPPLY_CHAIN_READ,
        }
    ),
}


def require_permission(permission: Permission):
    def authorize(
        current_user: AppUser = Depends(get_current_user),
    ) -> AppUser:
        permitted = ROLE_PERMISSIONS.get(current_user.role, frozenset())
        if permission not in permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return current_user

    return authorize
