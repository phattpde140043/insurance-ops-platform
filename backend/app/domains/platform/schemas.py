from pydantic import BaseModel


class OrganizationOut(BaseModel):
    id: str
    name: str
    created_at: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    organization_id: str
    created_at: str


class CreateUserIn(BaseModel):
    email: str
    name: str
    role: str = "employee"


class MeOut(BaseModel):
    user_id: str
    organization_id: str
    role: str
    permissions: list[str]


class AuditEventOut(BaseModel):
    id: str
    organization_id: str
    actor_user_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict
    created_at: str
