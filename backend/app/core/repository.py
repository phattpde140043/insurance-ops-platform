from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get(self, record_id: str) -> ModelT | None:
        return await self.session.get(self.model, record_id)

    async def get_for_org(self, organization_id: str, record_id: str) -> ModelT | None:
        statement = self._tenant_statement(organization_id).where(
            self.model.id == record_id  # type: ignore[attr-defined]
        )
        return await self.session.scalar(statement)

    async def list_for_org(
        self, organization_id: str, *, limit: int = 50, offset: int = 0
    ) -> Sequence[ModelT]:
        statement = self._tenant_statement(organization_id).limit(limit).offset(offset)
        result = await self.session.scalars(statement)
        return result.all()

    async def add(self, record: ModelT) -> ModelT:
        self.session.add(record)
        await self.session.flush()
        return record

    async def flush(self) -> None:
        await self.session.flush()

    def _tenant_statement(self, organization_id: str) -> Select[Any]:
        return select(self.model).where(  # type: ignore[arg-type]
            self.model.organization_id == organization_id  # type: ignore[attr-defined]
        )

