from dataclasses import dataclass


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: str
    organization_id: str
    role: str
    permissions: tuple[str, ...]


@dataclass(frozen=True)
class TenantContext:
    organization_id: str

