from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.platform.models import AuditEvent, Membership, Role, User
from app.domains.platform.repositories import AuditEventRepository
from app.domains.platform.schemas import CreateUserIn


def iso_or_empty(value) -> str:
    return value.isoformat() if value is not None else ""


class AdminUserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_log = AuditLogService(session)
        self.audit_events = AuditEventRepository(session)

    async def list_users(
        self, organization_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        statement = (
            select(User, Membership, Role)
            .join(Membership, Membership.user_id == User.id)
            .join(Role, Role.id == Membership.role_id)
            .where(Membership.organization_id == organization_id)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = await self.session.execute(statement)
        return [
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": role.key,
                "organization_id": membership.organization_id,
                "created_at": iso_or_empty(user.created_at),
            }
            for user, membership, role in rows.all()
        ]

    async def create_user(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        payload: CreateUserIn,
    ) -> dict:
        role = await self.session.scalar(
            select(Role).where(Role.organization_id == organization_id, Role.key == payload.role)
        )
        if role is None:
            role = Role(
                id=new_id("role"),
                organization_id=organization_id,
                key=payload.role,
                name=payload.role.title(),
                description="Created automatically by admin user service",
            )
            self.session.add(role)
            await self.session.flush()

        user = User(
            id=new_id("user"),
            email=payload.email,
            name=payload.name,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()

        membership = Membership(
            id=new_id("membership"),
            organization_id=organization_id,
            user_id=user.id,
            role_id=role.id,
            status="active",
        )
        self.session.add(membership)
        await self.session.flush()

        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="user.created",
                resource_type="user",
                resource_id=user.id,
                metadata={"role": payload.role},
            )
        )
        await self.session.commit()

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": payload.role,
            "organization_id": organization_id,
            "created_at": iso_or_empty(user.created_at),
        }

    async def request_password_reset(
        self, *, organization_id: str, actor_user_id: str, user_id: str
    ) -> None:
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="user.password_reset_requested",
                resource_type="user",
                resource_id=user_id,
            )
        )
        await self.session.commit()

    async def list_audit_events(
        self, organization_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        events = await self.audit_events.list_recent_for_org(
            organization_id, limit=limit, offset=offset
        )
        return [self._serialize_audit_event(event) for event in events]

    def _serialize_audit_event(self, event: AuditEvent) -> dict:
        return {
            "id": event.id,
            "organization_id": event.organization_id,
            "actor_user_id": event.actor_user_id or "",
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "metadata": event.metadata_json,
            "created_at": iso_or_empty(event.created_at),
        }
