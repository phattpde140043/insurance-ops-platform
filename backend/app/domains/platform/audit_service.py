from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.platform.models import AuditEvent
from app.domains.platform.repositories import AuditEventRepository


@dataclass(frozen=True)
class AuditEventCreate:
    organization_id: str
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None


class AuditLogService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AuditEventRepository(session)

    async def record(self, payload: AuditEventCreate) -> AuditEvent:
        event = AuditEvent(
            id=new_id("audit"),
            organization_id=payload.organization_id,
            actor_user_id=payload.actor_user_id,
            action=payload.action,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            metadata_json=payload.metadata,
            ip_address=payload.ip_address,
            user_agent=payload.user_agent,
        )
        return await self.repository.add(event)
