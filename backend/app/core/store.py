from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DemoStore:
    """In-memory store for the vertical skeleton.

    Phase 1 replaces this with SQLAlchemy repositories while preserving API shapes.
    """

    def __init__(self) -> None:
        self.organizations: list[dict[str, Any]] = [
            {
                "id": "org_demo",
                "name": "Insurance Operations Demo Organization",
                "created_at": utc_now(),
            }
        ]
        self.users: list[dict[str, Any]] = [
            {
                "id": "user_admin",
                "email": "admin@example.com",
                "name": "Demo Admin",
                "role": "admin",
                "organization_id": "org_demo",
                "created_at": utc_now(),
            },
            {
                "id": "user_employee",
                "email": "employee@example.com",
                "name": "Demo Employee",
                "role": "employee",
                "organization_id": "org_demo",
                "created_at": utc_now(),
            },
            {
                "id": "user_customer",
                "email": "customer@example.com",
                "name": "Demo Customer",
                "role": "customer",
                "organization_id": "org_demo",
                "created_at": utc_now(),
            },
        ]
        self.audit_events: list[dict[str, Any]] = []
        self.insurance_plans: list[dict[str, Any]] = [
            {
                "id": "plan_health_basic",
                "organization_id": "org_demo",
                "name": "Health Basic",
                "premium": 350000,
                "status": "active",
                "created_at": utc_now(),
            }
        ]
        self.customers: list[dict[str, Any]] = [
            {
                "id": "customer_lan",
                "organization_id": "org_demo",
                "name": "Nguyen Thi Lan",
                "email": "lan@example.com",
                "phone": "0900000001",
                "assigned_employee_id": "user_employee",
                "created_at": utc_now(),
            }
        ]
        self.policies: list[dict[str, Any]] = []
        self.incidents: list[dict[str, Any]] = []
        self.knowledge_documents: list[dict[str, Any]] = []
        self.chat_messages: list[dict[str, Any]] = []

    def list_for_org(self, collection: str, organization_id: str) -> list[dict[str, Any]]:
        records = getattr(self, collection)
        return [deepcopy(item) for item in records if item.get("organization_id") == organization_id]

    def add(self, collection: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": payload.get("id", f"{collection}_{uuid4().hex[:10]}"),
            "created_at": utc_now(),
            **payload,
        }
        getattr(self, collection).append(record)
        return deepcopy(record)

    def audit(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.add(
            "audit_events",
            {
                "organization_id": organization_id,
                "actor_user_id": actor_user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "metadata": metadata or {},
            },
        )


store = DemoStore()
