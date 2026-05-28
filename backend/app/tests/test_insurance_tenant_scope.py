from types import SimpleNamespace

import pytest

from app.domains.insurance.customer_policy_service import InsuranceCustomerPolicyService
from app.tests.support.tenant_isolation import (
    TenantActor,
    assert_customer_scope,
    assert_only_tenant_records,
)


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.customers = [
            SimpleNamespace(
                id="customer_alpha_1",
                organization_id="org_alpha",
                name="Alpha One",
                email="alpha1@example.com",
                phone=None,
                created_at=None,
            ),
            SimpleNamespace(
                id="customer_alpha_2",
                organization_id="org_alpha",
                name="Alpha Two",
                email="alpha2@example.com",
                phone=None,
                created_at=None,
            ),
            SimpleNamespace(
                id="customer_beta_1",
                organization_id="org_beta",
                name="Beta One",
                email="beta1@example.com",
                phone=None,
                created_at=None,
            ),
        ]

    async def list_for_org(self, organization_id: str, *, limit: int = 50):
        return [
            customer
            for customer in self.customers
            if customer.organization_id == organization_id
        ][:limit]


class FakeAssignmentRepository:
    async def list_customer_ids_for_employee(
        self, organization_id: str, employee_user_id: str
    ) -> set[str]:
        if organization_id == "org_alpha" and employee_user_id == "user_employee":
            return {"customer_alpha_2"}
        return set()


def build_customer_policy_service() -> InsuranceCustomerPolicyService:
    service = InsuranceCustomerPolicyService.__new__(InsuranceCustomerPolicyService)
    service.customers = FakeCustomerRepository()
    service.assignments = FakeAssignmentRepository()
    return service


@pytest.mark.asyncio
async def test_admin_customer_list_is_tenant_scoped() -> None:
    actor = TenantActor(
        organization_id="org_alpha",
        user_id="user_admin",
        role="admin",
    )
    service = build_customer_policy_service()

    result = await service.list_customers(actor.organization_id)

    assert_only_tenant_records(result, actor.organization_id)
    assert {customer["id"] for customer in result} == {
        "customer_alpha_1",
        "customer_alpha_2",
    }


@pytest.mark.asyncio
async def test_employee_customer_list_is_object_scoped() -> None:
    actor = TenantActor(
        organization_id="org_alpha",
        user_id="user_employee",
        role="employee",
    )
    service = build_customer_policy_service()

    result = await service.list_customers(
        actor.organization_id,
        employee_user_id=actor.user_id,
    )

    assert_only_tenant_records(result, actor.organization_id)
    assert_customer_scope(result, ["customer_alpha_2"])
    assert [customer["id"] for customer in result] == ["customer_alpha_2"]
