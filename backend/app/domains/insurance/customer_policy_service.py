from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.insurance.models import InsuranceCustomer, InsurancePolicy
from app.domains.insurance.repositories import (
    InsuranceCustomerRepository,
    InsuranceEmployeeAssignmentRepository,
    InsurancePlanRepository,
    InsurancePolicyRepository,
)
from app.domains.insurance.schemas import CreateCustomerIn, CreatePolicyIn
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.shared.idempotency_service import IdempotencyService
from app.domains.shared.outbox_service import DomainOutboxService


class InsuranceCustomerPolicyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = InsuranceCustomerRepository(session)
        self.assignments = InsuranceEmployeeAssignmentRepository(session)
        self.plans = InsurancePlanRepository(session)
        self.policies = InsurancePolicyRepository(session)
        self.audit_log = AuditLogService(session)
        self.outbox = DomainOutboxService(session)
        self.idempotency = IdempotencyService(session)

    async def list_customers(
        self,
        organization_id: str,
        *,
        employee_user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        customers = await self.customers.list_for_org(organization_id, limit=limit)
        if employee_user_id is not None:
            allowed_customer_ids = await self.assignments.list_customer_ids_for_employee(
                organization_id, employee_user_id
            )
            customers = [
                customer
                for customer in customers
                if customer.id in allowed_customer_ids
            ]
        return [self._serialize_customer(customer) for customer in customers]

    async def create_customer(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        payload: CreateCustomerIn,
    ) -> dict:
        customer = InsuranceCustomer(
            id=new_id("customer"),
            organization_id=organization_id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
        )
        await self.customers.add(customer)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.customer_created",
                resource_type="insurance_customer",
                resource_id=customer.id,
            )
        )
        await self.session.commit()
        return self._serialize_customer(customer)

    async def list_policies(self, organization_id: str, *, limit: int = 50) -> list[dict]:
        policies = await self.policies.list_for_org(organization_id, limit=limit)
        return [self._serialize_policy(policy) for policy in policies]

    async def create_policy(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        idempotency_key: str,
        payload: CreatePolicyIn,
    ) -> dict:
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.create_policy",
            idempotency_key=idempotency_key,
            fingerprint_payload=payload.model_dump(),
        )
        if reservation.replayed and reservation.record.resource_id:
            existing = await self.policies.get_for_org(
                organization_id, reservation.record.resource_id
            )
            if existing is not None:
                return self._serialize_policy(existing)
        customer = await self.customers.get_for_org(organization_id, payload.customer_id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "customer_not_found",
                    "message": "Insurance customer was not found.",
                },
            )
        plan = await self.plans.get_for_org(organization_id, payload.plan_id)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "plan_not_found",
                    "message": "Insurance plan was not found.",
                },
            )
        policy = InsurancePolicy(
            id=new_id("policy"),
            organization_id=organization_id,
            customer_id=payload.customer_id,
            plan_id=payload.plan_id,
            status=payload.status,
            start_date=date.fromisoformat(payload.start_date),
        )
        await self.policies.add(policy)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.policy_created",
                resource_type="insurance_policy",
                resource_id=policy.id,
                metadata={"customer_id": payload.customer_id, "plan_id": payload.plan_id},
            )
        )
        if policy.status == "active":
            await self.outbox.append(
                organization_id=organization_id,
                event_type="PolicyActivated",
                aggregate_type="insurance_policy",
                aggregate_id=policy.id,
                producer_module="insurance",
                payload={"customer_id": payload.customer_id},
                idempotency_key=idempotency_key,
            )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_policy",
            resource_id=policy.id,
        )
        await self.session.commit()
        return self._serialize_policy(policy)

    def _serialize_customer(self, customer: InsuranceCustomer) -> dict:
        return {
            "id": customer.id,
            "organization_id": customer.organization_id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "assigned_employee_id": None,
            "created_at": customer.created_at.isoformat() if customer.created_at else "",
        }

    def _serialize_policy(self, policy: InsurancePolicy) -> dict:
        return {
            "id": policy.id,
            "organization_id": policy.organization_id,
            "customer_id": policy.customer_id,
            "plan_id": policy.plan_id,
            "status": policy.status,
            "start_date": policy.start_date.isoformat(),
            "created_at": policy.created_at.isoformat() if policy.created_at else "",
        }
