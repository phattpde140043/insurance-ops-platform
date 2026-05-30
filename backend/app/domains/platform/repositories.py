from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.domains.platform.models import AuditEvent, Organization, User


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Organization)

    async def list_all(self) -> Sequence[Organization]:
        result = await self.session.scalars(select(Organization))
        return result.all()

    async def get_by_slug(self, slug: str) -> Organization | None:
        return await self.session.scalar(select(Organization).where(Organization.slug == slug))


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def get_by_google_subject(self, google_subject: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.google_subject == google_subject)
        )


class AuditEventRepository(BaseRepository[AuditEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditEvent)

    async def list_recent_for_org(
        self, organization_id: str, *, limit: int = 50, offset: int = 0
    ) -> Sequence[AuditEvent]:
        statement = (
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(statement)
        return result.all()
