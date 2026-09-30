import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from anyio import to_thread
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings

settings = get_settings()
password_hasher = PasswordHasher()
JWT_ALGORITHM = "HS256"


async def hash_password(password: str) -> str:
    return await to_thread.run_sync(password_hasher.hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    try:
        return await to_thread.run_sync(password_hasher.verify, password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    *,
    user_id: UUID,
    organization_id: UUID,
    role: str,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(payload, settings.auth_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.auth_secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "iat", "sub", "org", "type"]},
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("invalid token type")

    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
