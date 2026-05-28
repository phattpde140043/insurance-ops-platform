from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select

from app.core.repository import BaseRepository
from app.domains.insurance.models import (
    InsuranceClaimTransition,
    InsuranceCustomer,
    InsuranceEmployeeAssignment,
    InsuranceIncidentReport,
    InsuranceAppointment,
    InsuranceConversation,
    InsuranceMessage,
    InsurancePlan,
    InsurancePolicy,
)


class InsurancePlanRepository(BaseRepository[InsurancePlan]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsurancePlan)


class InsuranceCustomerRepository(BaseRepository[InsuranceCustomer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsuranceCustomer)

    async def get_by_linked_user_id(
        self, organization_id: str, user_id: str
    ) -> InsuranceCustomer | None:
        statement = select(InsuranceCustomer).where(
            InsuranceCustomer.organization_id == organization_id,
            InsuranceCustomer.linked_user_id == user_id,
        )
        return await self.session.scalar(statement)


class InsurancePolicyRepository(BaseRepository[InsurancePolicy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsurancePolicy)

    async def list_for_customer(
        self, organization_id: str, customer_id: str, *, limit: int = 10
    ) -> list[InsurancePolicy]:
        result = await self.session.scalars(
            select(InsurancePolicy)
            .where(
                InsurancePolicy.organization_id == organization_id,
                InsurancePolicy.customer_id == customer_id,
            )
            .order_by(InsurancePolicy.created_at.desc())
            .limit(limit)
        )
        return list(result.all())

    async def get_open_for_claim(
        self, organization_id: str, claim_id: str
    ) -> InsuranceConversation | None:
        statement = select(InsuranceConversation).where(
            InsuranceConversation.organization_id == organization_id,
            InsuranceConversation.claim_id == claim_id,
            InsuranceConversation.status == "open",
        )
        return await self.session.scalar(statement)


class InsuranceEmployeeAssignmentRepository(BaseRepository[InsuranceEmployeeAssignment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsuranceEmployeeAssignment)

    async def list_customer_ids_for_employee(
        self, organization_id: str, employee_user_id: str
    ) -> set[str]:
        result = await self.session.scalars(
            select(InsuranceEmployeeAssignment.customer_id).where(
                InsuranceEmployeeAssignment.organization_id == organization_id,
                InsuranceEmployeeAssignment.employee_user_id == employee_user_id,
                InsuranceEmployeeAssignment.status == "active",
            )
        )
        return set(result.all())

    async def get_active_for_customer(
        self, organization_id: str, customer_id: str
    ) -> InsuranceEmployeeAssignment | None:
        statement = select(InsuranceEmployeeAssignment).where(
            InsuranceEmployeeAssignment.organization_id == organization_id,
            InsuranceEmployeeAssignment.customer_id == customer_id,
            InsuranceEmployeeAssignment.status == "active",
        )
        return await self.session.scalar(statement)


class InsuranceIncidentReportRepository(BaseRepository[InsuranceIncidentReport]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsuranceIncidentReport)

    async def list_for_customer(
        self, organization_id: str, customer_id: str, *, limit: int = 10
    ) -> list[InsuranceIncidentReport]:
        result = await self.session.scalars(
            select(InsuranceIncidentReport)
            .where(
                InsuranceIncidentReport.organization_id == organization_id,
                InsuranceIncidentReport.customer_id == customer_id,
            )
            .order_by(InsuranceIncidentReport.created_at.desc())
            .limit(limit)
        )
        return list(result.all())


class InsuranceClaimTransitionRepository(BaseRepository[InsuranceClaimTransition]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsuranceClaimTransition)

    async def list_for_claim(
        self, organization_id: str, claim_id: str, *, limit: int = 100
    ) -> list[InsuranceClaimTransition]:
        result = await self.session.scalars(
            select(InsuranceClaimTransition)
            .where(
                InsuranceClaimTransition.organization_id == organization_id,
                InsuranceClaimTransition.claim_id == claim_id,
            )
            .order_by(InsuranceClaimTransition.created_at.asc())
            .limit(limit)
        )
        return list(result.all())


class InsuranceAppointmentRepository(BaseRepository[InsuranceAppointment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsuranceAppointment)

    async def list_for_customer(
        self, organization_id: str, customer_id: str, *, limit: int = 10
    ) -> list[InsuranceAppointment]:
        result = await self.session.scalars(
            select(InsuranceAppointment)
            .where(
                InsuranceAppointment.organization_id == organization_id,
                InsuranceAppointment.customer_id == customer_id,
            )
            .order_by(InsuranceAppointment.scheduled_at.asc())
            .limit(limit)
        )
        return list(result.all())


class InsuranceConversationRepository(BaseRepository[InsuranceConversation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsuranceConversation)

    async def list_for_customer(
        self, organization_id: str, customer_id: str, *, limit: int = 10
    ) -> list[InsuranceConversation]:
        result = await self.session.scalars(
            select(InsuranceConversation)
            .where(
                InsuranceConversation.organization_id == organization_id,
                InsuranceConversation.customer_id == customer_id,
            )
            .order_by(InsuranceConversation.created_at.desc())
            .limit(limit)
        )
        return list(result.all())

    async def list_visible_for_employee(
        self,
        organization_id: str,
        employee_user_id: str,
        customer_ids: set[str],
        *,
        limit: int = 25,
    ) -> list[InsuranceConversation]:
        visibility_conditions = [
            InsuranceConversation.employee_user_id == employee_user_id,
        ]
        if customer_ids:
            visibility_conditions.append(InsuranceConversation.customer_id.in_(customer_ids))
        result = await self.session.scalars(
            select(InsuranceConversation)
            .where(
                InsuranceConversation.organization_id == organization_id,
                or_(*visibility_conditions),
            )
            .order_by(InsuranceConversation.created_at.desc())
            .limit(limit)
        )
        return list(result.all())


class InsuranceMessageRepository(BaseRepository[InsuranceMessage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InsuranceMessage)

    async def list_for_conversation(
        self,
        organization_id: str,
        conversation_id: str,
        *,
        limit: int = 50,
    ) -> list[InsuranceMessage]:
        result = await self.session.scalars(
            select(InsuranceMessage)
            .where(
                InsuranceMessage.organization_id == organization_id,
                InsuranceMessage.conversation_id == conversation_id,
            )
            .order_by(InsuranceMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.all())
