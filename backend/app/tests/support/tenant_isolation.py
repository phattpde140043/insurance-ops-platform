from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class TenantActor:
    organization_id: str
    user_id: str
    role: str


def assert_only_tenant_records(
    records: Iterable[Mapping[str, object]], organization_id: str
) -> None:
    leaked = [
        record
        for record in records
        if record.get("organization_id") != organization_id
    ]
    assert leaked == [], f"records leaked across tenant boundary: {leaked}"


def assert_customer_scope(
    records: Iterable[Mapping[str, object]], allowed_customer_ids: Sequence[str]
) -> None:
    allowed = set(allowed_customer_ids)
    leaked = [
        record
        for record in records
        if record.get("id") not in allowed
        and record.get("customer_id") not in allowed
    ]
    assert leaked == [], f"records leaked outside customer scope: {leaked}"


def assert_forbidden_status(status_code: int) -> None:
    assert status_code == 403, f"expected 403 forbidden, got {status_code}"
