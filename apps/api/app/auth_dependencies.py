from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import OrganizationMember, User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    display_name: str | None
    organization_id: UUID
    role: str


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
        organization_id = UUID(str(payload["org"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid access token",
        ) from None

    statement = (
        select(User, OrganizationMember)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(
            User.id == user_id,
            User.is_active.is_(True),
            OrganizationMember.organization_id == organization_id,
        )
    )
    row = (await session.execute(statement)).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session no longer has access",
        )

    user, membership = row

    return Principal(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        organization_id=membership.organization_id,
        role=membership.role,
    )


def require_roles(*allowed_roles: str):
    async def dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient permissions",
            )
        return principal

    return dependency


async def require_path_organization(
    organization_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if principal.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cross-tenant access denied",
        )

    return principal
