from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.insurance.models import InsurancePlan
from app.domains.insurance.repositories import InsurancePlanRepository
from app.domains.insurance.schemas import CreateInsurancePlanIn
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService


class InsurancePlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = InsurancePlanRepository(session)
        self.audit_log = AuditLogService(session)

    async def list_plans(self, organization_id: str, *, limit: int = 50) -> list[dict]:
        plans = await self.repository.list_for_org(organization_id, limit=limit)
        return [self._serialize(plan) for plan in plans]

    async def create_plan(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        payload: CreateInsurancePlanIn,
    ) -> dict:
        plan = InsurancePlan(
            id=new_id("plan"),
            organization_id=organization_id,
            name=payload.name,
            premium=payload.premium,
            status=payload.status,
        )
        await self.repository.add(plan)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.plan_created",
                resource_type="insurance_plan",
                resource_id=plan.id,
                metadata={"premium": payload.premium, "status": payload.status},
            )
        )
        await self.session.commit()
        return self._serialize(plan)

    def _serialize(self, plan: InsurancePlan) -> dict:
        return {
            "id": plan.id,
            "organization_id": plan.organization_id,
            "name": plan.name,
            "premium": plan.premium,
            "status": plan.status,
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
        }
