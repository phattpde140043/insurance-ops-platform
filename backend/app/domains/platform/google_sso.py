from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import settings


DEMO_GOOGLE_ID_TOKEN = "demo_google_id_token"


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


def get_google_token_verifier() -> GoogleTokenVerifier:
    if settings.google_token_verifier_mode == "google":
        return GoogleAuthTokenVerifier()
    return DemoGoogleTokenVerifier()
