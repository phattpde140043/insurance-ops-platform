from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth_types import AuthPrincipal
from app.core.config import settings
from app.core.permissions import ROLE_PERMISSIONS, has_permission
from app.core.session import decode_access_token


@dataclass(frozen=True)
class RequestContext:
    principal: AuthPrincipal

    @property
    def organization_id(self) -> str:
        return self.principal.organization_id

    @property
    def user_id(self) -> str:
        return self.principal.user_id

    @property
    def role(self) -> str:
        return self.principal.role

    @property
    def permissions(self) -> tuple[str, ...]:
        return self.principal.permissions


class AuthProvider(Protocol):
    async def authenticate(self) -> AuthPrincipal:
        """Return the authenticated principal for the current request."""


bearer_scheme = HTTPBearer(auto_error=False)


class DemoHeaderAuthProvider:
    def __init__(self, organization_id: str, user_id: str, role: str) -> None:
        self.organization_id = organization_id
        self.user_id = user_id
        self.role = role

    async def authenticate(self) -> AuthPrincipal:
        if self.role not in ROLE_PERMISSIONS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "invalid_demo_role",
                    "message": "The demo role is not recognized.",
                },
            )
        return AuthPrincipal(
            organization_id=self.organization_id,
            user_id=self.user_id,
            role=self.role,
            permissions=ROLE_PERMISSIONS.get(self.role, ()),
        )


class StaticAuthProvider:
    def __init__(self, principal: AuthPrincipal) -> None:
        self.principal = principal

    async def authenticate(self) -> AuthPrincipal:
        return self.principal


async def get_auth_provider(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    organization_id: Annotated[str, Header(alias="X-Organization-Id")] = "org_demo",
    header_user_id: Annotated[str, Header(alias="X-User-Id")] = "user_admin",
    role: Annotated[str, Header(alias="X-Role")] = "admin",
) -> AuthProvider:
    if credentials is not None:
        principal = decode_access_token(credentials.credentials)
        return StaticAuthProvider(principal)

    if not _demo_header_auth_allowed():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "missing_access_token",
                "message": "Bearer authentication is required.",
            },
        )

    return DemoHeaderAuthProvider(
        organization_id=organization_id,
        user_id=header_user_id,
        role=role,
    )


def _demo_header_auth_allowed() -> bool:
    return settings.demo_header_auth_enabled and settings.environment.lower() in {
        "local",
        "dev",
        "development",
        "test",
    }


async def get_request_context(
    auth_provider: Annotated[AuthProvider, Depends(get_auth_provider)]
) -> RequestContext:
    principal = await auth_provider.authenticate()
    return RequestContext(principal=principal)


def require_roles(*roles: str):
    async def dependency(
        context: Annotated[RequestContext, Depends(get_request_context)]
    ) -> RequestContext:
        if context.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "permission_denied",
                    "message": "You do not have permission to access this resource.",
                },
            )
        return context

    return dependency


def require_permissions(*permissions: str):
    async def dependency(
        context: Annotated[RequestContext, Depends(get_request_context)]
    ) -> RequestContext:
        if not has_permission(context.permissions, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "permission_denied",
                    "message": "You do not have the required permission.",
                    "required_permissions": list(permissions),
                },
            )
        return context

    return dependency
