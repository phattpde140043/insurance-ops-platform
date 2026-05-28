from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import KnowledgeBase, KnowledgeDocument
from app.domains.insurance.models import (
    InsuranceCustomer,
    InsuranceEmployeeAssignment,
    InsuranceIncidentReport,
    InsurancePlan,
    InsurancePolicy,
)
from app.domains.platform.models import (
    Membership,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
)


ORG_ID = "org_demo"
ADMIN_ID = "user_admin"
EMPLOYEE_ID = "user_employee"
CUSTOMER_USER_ID = "user_customer"


async def add_if_missing(session: AsyncSession, model: type, record_id: str, **values):
    existing = await session.get(model, record_id)
    if existing is not None:
        return existing

    record = model(id=record_id, **values)
    session.add(record)
    return record


async def seed_demo_data(session: AsyncSession) -> None:
    await add_if_missing(
        session,
        Organization,
        ORG_ID,
        name="Insurance Operations Demo Organization",
        slug="insurance-ops-demo",
        status="active",
    )

    await add_if_missing(
        session,
        User,
        ADMIN_ID,
        email="admin@example.com",
        name="Demo Admin",
        google_subject="google_admin_demo",
        is_active=True,
    )
    await add_if_missing(
        session,
        User,
        EMPLOYEE_ID,
        email="employee@example.com",
        name="Demo Employee",
        google_subject="google_employee_demo",
        is_active=True,
    )
    await add_if_missing(
        session,
        User,
        CUSTOMER_USER_ID,
        email="customer@example.com",
        name="Demo Customer",
        google_subject="google_customer_demo",
        is_active=True,
    )

    roles = [
        ("role_admin", "admin", "Admin"),
        ("role_employee", "employee", "Employee"),
        ("role_customer", "customer", "Customer"),
    ]
    for role_id, key, name in roles:
        await add_if_missing(
            session,
            Role,
            role_id,
            organization_id=ORG_ID,
            key=key,
            name=name,
            description=f"Demo {name} role",
        )

    permissions = [
        ("perm_all", "*", "Full administrative access"),
        ("perm_insurance_write", "insurance:write", "Manage insurance operations"),
        ("perm_dashboard_read", "dashboard:read", "Read dashboards"),
        ("perm_incident_create", "incident:create", "Create incident reports"),
        ("perm_chat_write", "chat:write", "Use chatbot and support chat"),
    ]
    for permission_id, key, description in permissions:
        await add_if_missing(
            session,
            Permission,
            permission_id,
            key=key,
            description=description,
        )

    role_permissions = [
        ("role_perm_admin_all", "role_admin", "perm_all"),
        ("role_perm_employee_insurance", "role_employee", "perm_insurance_write"),
        ("role_perm_employee_dashboard", "role_employee", "perm_dashboard_read"),
        ("role_perm_customer_incident", "role_customer", "perm_incident_create"),
        ("role_perm_customer_chat", "role_customer", "perm_chat_write"),
    ]
    for record_id, role_id, permission_id in role_permissions:
        await add_if_missing(
            session,
            RolePermission,
            record_id,
            role_id=role_id,
            permission_id=permission_id,
        )

    memberships = [
        ("membership_admin", ADMIN_ID, "role_admin"),
        ("membership_employee", EMPLOYEE_ID, "role_employee"),
        ("membership_customer", CUSTOMER_USER_ID, "role_customer"),
    ]
    for record_id, user_id, role_id in memberships:
        await add_if_missing(
            session,
            Membership,
            record_id,
            organization_id=ORG_ID,
            user_id=user_id,
            role_id=role_id,
            status="active",
        )

    await add_if_missing(
        session,
        InsurancePlan,
        "plan_health_basic",
        organization_id=ORG_ID,
        name="Health Basic",
        premium=350000,
        status="active",
        description="Basic health insurance plan for demo customers",
    )
    await add_if_missing(
        session,
        InsuranceCustomer,
        "customer_lan",
        organization_id=ORG_ID,
        name="Nguyen Thi Lan",
        email="lan@example.com",
        phone="0900000001",
        linked_user_id=CUSTOMER_USER_ID,
    )
    await add_if_missing(
        session,
        InsuranceEmployeeAssignment,
        "assignment_lan_employee",
        organization_id=ORG_ID,
        customer_id="customer_lan",
        employee_user_id=EMPLOYEE_ID,
        status="active",
    )
    await add_if_missing(
        session,
        InsurancePolicy,
        "policy_lan_health",
        organization_id=ORG_ID,
        customer_id="customer_lan",
        plan_id="plan_health_basic",
        status="active",
        start_date=date(2026, 5, 1),
    )
    await add_if_missing(
        session,
        InsuranceIncidentReport,
        "incident_lan_demo",
        organization_id=ORG_ID,
        customer_id="customer_lan",
        policy_id="policy_lan_health",
        incident_type="medical",
        description="Demo medical incident for workflow testing",
        status="reported",
    )

    await add_if_missing(
        session,
        KnowledgeBase,
        "kb_insurance_demo",
        organization_id=ORG_ID,
        name="Insurance Demo Wiki",
        status="active",
    )
    await add_if_missing(
        session,
        KnowledgeDocument,
        "knowledge_doc_policy_demo",
        organization_id=ORG_ID,
        knowledge_base_id="kb_insurance_demo",
        title="Demo Insurance Policy FAQ",
        source_type="pdf",
        status="uploaded",
    )

    await session.commit()
