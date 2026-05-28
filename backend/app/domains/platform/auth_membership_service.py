from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_types import AuthPrincipal
from app.core.permissions import ROLE_PERMISSIONS
from app.domains.platform.google_sso import GoogleProfile
from app.domains.platform.models import Membership, Permission, Role, RolePermission, User


class AuthMembershipService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def principal_from_google_profile(self, profile: GoogleProfile) -> AuthPrincipal:
        user = await self.session.scalar(
            select(User).where(
                (User.google_subject == profile.subject) | (User.email == profile.email)
            )
        )
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "user_not_allowed",
                    "message": "No active user is linked to this Google account.",
                },
            )

        row = (
            await self.session.execute(
                select(Membership, Role)
                .join(Role, Role.id == Membership.role_id)
                .where(Membership.user_id == user.id, Membership.status == "active")
                .limit(1)
            )
        ).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "membership_not_found",
                    "message": "User does not have an active organization membership.",
                },
            )

        membership, role = row
        permissions = await self._load_permissions(role)
        return AuthPrincipal(
            user_id=user.id,
            organization_id=membership.organization_id,
            role=role.key,
            permissions=permissions,
        )

    async def _load_permissions(self, role: Role) -> tuple[str, ...]:
        result = await self.session.scalars(
            select(Permission.key)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
        permissions = tuple(result.all())
        return permissions or ROLE_PERMISSIONS.get(role.key, ())

