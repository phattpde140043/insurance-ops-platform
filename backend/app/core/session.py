from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings
from app.core.auth_types import AuthPrincipal


def issue_access_token(principal: AuthPrincipal) -> dict[str, Any]:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expires_minutes
    )
    payload = {
        "sub": principal.user_id,
        "org": principal.organization_id,
        "role": principal.role,
        "permissions": list(principal.permissions),
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expires_minutes * 60,
    }


def decode_access_token(token: str) -> AuthPrincipal:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_access_token",
                "message": "The access token is invalid or expired.",
            },
        ) from exc

    user_id = payload.get("sub")
    organization_id = payload.get("org")
    role = payload.get("role")
    permissions = payload.get("permissions", [])

    if not user_id or not organization_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_access_token_claims",
                "message": "The access token is missing required claims.",
            },
        )

    return AuthPrincipal(
        user_id=user_id,
        organization_id=organization_id,
        role=role,
        permissions=tuple(permissions),
    )
