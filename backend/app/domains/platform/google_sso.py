from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Protocol

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt

from app.core.config import settings


DEMO_GOOGLE_ID_TOKEN = "demo_google_id_token"
DEMO_GOOGLE_CLIENT_ID = "demo-google-client-id"
PRODUCTION_LIKE_ENVIRONMENTS = {"prod", "production", "staging"}
GOOGLE_CALLBACK_STATE_PURPOSE = "google_oauth_callback"


@dataclass(frozen=True)
class GoogleProfile:
    subject: str
    email: str
    name: str
    avatar_url: str | None = None


class GoogleTokenVerifier(Protocol):
    async def verify_id_token(self, id_token: str) -> GoogleProfile:
        """Verify a Google ID token and return a normalized Google profile."""


class DemoGoogleTokenVerifier:
    async def verify_id_token(self, id_token: str) -> GoogleProfile:
        if id_token != DEMO_GOOGLE_ID_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "invalid_google_token",
                    "message": "The provided Google ID token is not valid in demo mode.",
                },
            )

        return GoogleProfile(
            subject="google_admin_demo",
            email="admin@example.com",
            name="Demo Admin",
            avatar_url=None,
        )


class GoogleAuthTokenVerifier:
    async def verify_id_token(self, id_token: str) -> GoogleProfile:
        try:
            payload = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                settings.google_client_id,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "invalid_google_token",
                    "message": "The provided Google ID token is invalid.",
                },
            ) from exc

        subject = payload.get("sub")
        email = payload.get("email")
        name = payload.get("name") or email
        if not subject or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "invalid_google_profile",
                    "message": "The Google ID token is missing required profile claims.",
                },
            )

        return GoogleProfile(
            subject=subject,
            email=email,
            name=name,
            avatar_url=payload.get("picture"),
        )


def issue_google_callback_state() -> str:
    validate_google_sso_configuration()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    return jwt.encode(
        {
            "purpose": GOOGLE_CALLBACK_STATE_PURPOSE,
            "nonce": token_urlsafe(24),
            "exp": expires_at,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_google_callback_state(state_token: str | None) -> None:
    if state_token is None:
        if _is_production_like():
            _raise_invalid_callback_state()
        return

    try:
        payload = jwt.decode(
            state_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise _invalid_callback_state_error() from exc

    if (
        payload.get("purpose") != GOOGLE_CALLBACK_STATE_PURPOSE
        or not payload.get("nonce")
    ):
        _raise_invalid_callback_state()


def validate_google_sso_configuration() -> None:
    mode = settings.google_token_verifier_mode.strip().lower()
    if mode == "disabled":
        _raise_configuration_error(
            code="google_sso_disabled",
            message="Google SSO is disabled.",
        )
    if mode == "demo":
        if _is_production_like():
            _raise_configuration_error(
                code="google_sso_demo_forbidden",
                message="Demo Google SSO is not allowed in production-like environments.",
            )
        return
    if mode != "google":
        _raise_configuration_error(
            code="invalid_google_verifier_mode",
            message="Google SSO verifier mode is not recognized.",
        )
    if (
        not settings.google_client_id.strip()
        or settings.google_client_id == DEMO_GOOGLE_CLIENT_ID
    ):
        _raise_configuration_error(
            code="missing_google_client_id",
            message="A production Google client id is required.",
        )
    if not settings.google_callback_url.strip():
        _raise_configuration_error(
            code="missing_google_callback_url",
            message="A Google callback URL is required.",
        )


def get_google_token_verifier() -> GoogleTokenVerifier:
    validate_google_sso_configuration()
    if settings.google_token_verifier_mode.strip().lower() == "google":
        return GoogleAuthTokenVerifier()
    return DemoGoogleTokenVerifier()


def _is_production_like() -> bool:
    return settings.environment.strip().lower() in PRODUCTION_LIKE_ENVIRONMENTS


def _raise_configuration_error(*, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": code, "message": message},
    )


def _invalid_callback_state_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "invalid_google_callback_state",
            "message": "The Google callback state is missing, invalid or expired.",
        },
    )


def _raise_invalid_callback_state() -> None:
    raise _invalid_callback_state_error()
