import re
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import Principal, get_current_principal
from app.config import get_settings
from app.db import get_session
from app.models import Organization, OrganizationMember, RefreshSession, User
from app.schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_expiration,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
    return f"{base[:100]}-{secrets.token_hex(3)}"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/auth",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
    )


def _token_response(
    *,
    user_id,
    organization_id,
    role: str,
) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
        ),
        expires_in=settings.access_token_minutes * 60,
    )


async def _create_refresh_session(
    *,
    session: AsyncSession,
    user_id,
) -> str:
    raw_token = generate_refresh_token()
    session.add(
        RefreshSession(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=refresh_expiration(),
        )
    )
    return raw_token


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    email = str(payload.email).lower()

    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        )

    user = User(
        email=email,
        display_name=payload.display_name,
        password_hash=await hash_password(payload.password),
    )
    organization = Organization(
        name=payload.organization_name,
        slug=_slugify(payload.organization_name),
    )

    session.add_all([user, organization])
    await session.flush()

    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=user.id,
        role="owner",
    )
    session.add(membership)

    refresh_token = await _create_refresh_session(
        session=session,
        user_id=user.id,
    )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="account could not be created",
        ) from None

    _set_refresh_cookie(response, refresh_token)

    return _token_response(
        user_id=user.id,
        organization_id=organization.id,
        role=membership.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    email = str(payload.email).lower()
    user = await session.scalar(select(User).where(User.email == email))

    if (
        user is None
        or not user.is_active
        or not await verify_password(user.password_hash, payload.password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    membership = await session.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.created_at.asc())
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user has no organization",
        )

    refresh_token = await _create_refresh_session(
        session=session,
        user_id=user.id,
    )
    await session.commit()
    _set_refresh_cookie(response, refresh_token)

    return _token_response(
        user_id=user.id,
        organization_id=membership.organization_id,
        role=membership.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias=settings.refresh_cookie_name,
    ),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token required",
        )

    token_hash = hash_refresh_token(refresh_token)
    refresh_session = await session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash)
    )

    now = datetime.now(timezone.utc)

    if (
        refresh_session is None
        or refresh_session.revoked_at is not None
        or refresh_session.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid refresh token",
        )

    user = await session.get(User, refresh_session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user is unavailable",
        )

    membership = await session.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.created_at.asc())
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user has no organization",
        )

    refresh_session.revoked_at = now
    next_refresh_token = await _create_refresh_session(
        session=session,
        user_id=user.id,
    )
    await session.commit()

    _set_refresh_cookie(response, next_refresh_token)

    return _token_response(
        user_id=user.id,
        organization_id=membership.organization_id,
        role=membership.role,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias=settings.refresh_cookie_name,
    ),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if refresh_token:
        stored_session = await session.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == hash_refresh_token(refresh_token)
            )
        )
        if stored_session is not None and stored_session.revoked_at is None:
            stored_session.revoked_at = datetime.now(timezone.utc)
            await session.commit()

    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Principal = Depends(get_current_principal),
) -> MeResponse:
    return MeResponse(
        user_id=principal.user_id,
        email=principal.email,
        display_name=principal.display_name,
        organization_id=principal.organization_id,
        role=principal.role,
    )
