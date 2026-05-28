from enum import StrEnum


class Permission(StrEnum):
    ADMIN_ALL = "*"
    INSURANCE_READ = "insurance:read"
    INSURANCE_WRITE = "insurance:write"
    DASHBOARD_READ = "dashboard:read"
    INCIDENT_CREATE = "incident:create"
    CHAT_WRITE = "chat:write"
    AI_MANAGE = "ai:manage"
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "admin": (Permission.ADMIN_ALL.value,),
    "employee": (
        Permission.INSURANCE_READ.value,
        Permission.INSURANCE_WRITE.value,
        Permission.DASHBOARD_READ.value,
        Permission.CHAT_WRITE.value,
    ),
    "customer": (
        Permission.INSURANCE_READ.value,
        Permission.INCIDENT_CREATE.value,
        Permission.CHAT_WRITE.value,
    ),
}


def has_permission(principal_permissions: tuple[str, ...], required: tuple[str, ...]) -> bool:
    if Permission.ADMIN_ALL.value in principal_permissions:
        return True
    return all(permission in principal_permissions for permission in required)
