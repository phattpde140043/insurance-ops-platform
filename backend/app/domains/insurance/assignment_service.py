from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.insurance.models import InsuranceEmployeeAssignment
from app.domains.insurance.repositories import (
    InsuranceCustomerRepository,
    InsuranceEmployeeAssignmentRepository,
)
from app.domains.insurance.schemas import CreateAssignmentIn
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService


class InsuranceAssignmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = InsuranceCustomerRepository(session)
        self.assignments = InsuranceEmployeeAssignmentRepository(session)
        self.audit_log = AuditLogService(session)

    async def create_assignment(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        payload: CreateAssignmentIn,
    ) -> dict:
        customer = await self.customers.get_for_org(organization_id, payload.customer_id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "customer_not_found",
                    "message": "Insurance customer was not found.",
                },
            )
        assignment = InsuranceEmployeeAssignment(
            id=new_id("assignment"),
            organization_id=organization_id,
            customer_id=payload.customer_id,
            employee_user_id=payload.employee_user_id,
            status=payload.status,
        )
        await self.assignments.add(assignment)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.employee_assigned",
                resource_type="insurance_customer",
                resource_id=payload.customer_id,
                metadata={"employee_user_id": payload.employee_user_id},
            )
        )
        await self.session.commit()
        return self._serialize(assignment)

    def _serialize(self, assignment: InsuranceEmployeeAssignment) -> dict:
        return {
            "id": assignment.id,
            "organization_id": assignment.organization_id,
            "customer_id": assignment.customer_id,
            "employee_user_id": assignment.employee_user_id,
            "status": assignment.status,
            "created_at": assignment.created_at.isoformat()
            if assignment.created_at
            else "",
        }

