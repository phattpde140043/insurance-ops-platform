import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import context
from app.core.auth_types import AuthPrincipal
from app.core.permissions import Permission
from app.core.session import issue_access_token


@pytest.mark.asyncio
async def test_demo_header_auth_is_allowed_in_local_mode(monkeypatch) -> None:
    monkeypatch.setattr(context.settings, "environment", "local")
    monkeypatch.setattr(context.settings, "demo_header_auth_enabled", True)

    provider = await context.get_auth_provider(
        credentials=None,
        organization_id="org_demo",
        header_user_id="user_employee",
        role="employee",
    )

    principal = await provider.authenticate()

    assert principal.organization_id == "org_demo"
    assert principal.user_id == "user_employee"
    assert principal.role == "employee"


@pytest.mark.asyncio
async def test_demo_header_auth_is_rejected_in_production_mode(monkeypatch) -> None:
    monkeypatch.setattr(context.settings, "environment", "production")
    monkeypatch.setattr(context.settings, "demo_header_auth_enabled", True)

    with pytest.raises(HTTPException) as exc:
        await context.get_auth_provider(
            credentials=None,
            organization_id="org_demo",
            header_user_id="user_admin",
            role="admin",
        )

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "missing_access_token"


@pytest.mark.asyncio
async def test_bearer_token_auth_works_in_production_mode(monkeypatch) -> None:
    monkeypatch.setattr(context.settings, "environment", "production")
    monkeypatch.setattr(context.settings, "demo_header_auth_enabled", False)
    token = issue_access_token(
        AuthPrincipal(
            organization_id="org_demo",
            user_id="user_admin",
            role="admin",
            permissions=(Permission.ADMIN_ALL.value,),
        )
    )["access_token"]

    provider = await context.get_auth_provider(
        credentials=HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        ),
        organization_id="ignored_org",
        header_user_id="ignored_user",
        role="customer",
    )

    principal = await provider.authenticate()

    assert principal.organization_id == "org_demo"
    assert principal.user_id == "user_admin"
    assert principal.role == "admin"


@pytest.mark.asyncio
async def test_malformed_bearer_token_is_rejected_in_production_mode(monkeypatch) -> None:
    monkeypatch.setattr(context.settings, "environment", "production")
    monkeypatch.setattr(context.settings, "demo_header_auth_enabled", False)

    with pytest.raises(HTTPException) as exc:
        await context.get_auth_provider(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="not-a-valid-jwt",
            ),
            organization_id="spoofed_org",
            header_user_id="spoofed_user",
            role="admin",
        )

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_invalid_demo_role_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(context.settings, "environment", "local")
    monkeypatch.setattr(context.settings, "demo_header_auth_enabled", True)

    provider = await context.get_auth_provider(
        credentials=None,
        organization_id="org_demo",
        header_user_id="user_admin",
        role="owner",
    )

    with pytest.raises(HTTPException) as exc:
        await provider.authenticate()

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "invalid_demo_role"
