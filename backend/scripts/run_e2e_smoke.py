import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from uuid import uuid4

from app.core.storage import issue_storage_download_token

API_BASE = os.getenv("SMOKE_API_BASE_URL", "http://localhost:8002/api/v1")
ORIGIN = API_BASE.split("/api/", 1)[0]


def headers(user_id: str, role: str, organization_id: str = "org_demo") -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Organization-Id": organization_id,
        "X-User-Id": user_id,
        "X-Role": role,
    }


def request_json(
    method: str,
    path: str,
    *,
    user_id: str,
    role: str,
    organization_id: str = "org_demo",
    payload: dict | None = None,
    idempotent: bool = False,
) -> dict:
    request_headers = headers(user_id, role, organization_id)
    if idempotent:
        request_headers["X-Idempotency-Key"] = f"smoke-{uuid4().hex}"
    request = Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=request_headers,
        method=method,
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read() or b"{}")


def expect_http_status(
    status_code: int,
    method: str,
    path: str,
    *,
    user_id: str,
    role: str,
    organization_id: str = "org_demo",
) -> None:
    try:
        request_json(
            method,
            path,
            user_id=user_id,
            role=role,
            organization_id=organization_id,
        )
    except HTTPError as exc:
        if exc.code == status_code:
            print(f"PASS expected {status_code}: {method} {path}")
            return
        raise
    raise AssertionError(f"Expected HTTP {status_code}: {method} {path}")


def main() -> None:
    portal = request_json("GET", "/insurance/portal/summary", user_id="user_customer", role="customer")
    assert portal["customer"]["id"] == "customer_lan"
    print("PASS customer portal summary")

    incident = request_json(
        "POST",
        "/insurance/incidents",
        user_id="user_customer",
        role="customer",
        idempotent=True,
        payload={
            "customer_id": "customer_lan",
            "incident_type": "medical",
            "description": "Smoke incident report",
        },
    )
    print(f"PASS customer incident report: {incident['id']}")

    queue = request_json("GET", "/insurance/queues/my", user_id="user_employee", role="employee")
    assert any(item["source_id"] == incident["id"] for item in queue["items"])
    print("PASS employee queue projection")

    claim = request_json(
        "POST",
        f"/insurance/claims/{incident['id']}/transitions",
        user_id="user_employee",
        role="employee",
        idempotent=True,
        payload={"to_state": "triage", "reason": "Smoke triage"},
    )
    assert claim["claim_state"] == "triage"
    print("PASS claim transition")

    conversation = request_json(
        "POST",
        "/insurance/conversations",
        user_id="user_employee",
        role="employee",
        idempotent=True,
        payload={"customer_id": "customer_lan", "claim_id": incident["id"]},
    )
    request_json(
        "POST",
        f"/insurance/conversations/{conversation['id']}/messages",
        user_id="user_customer",
        role="customer",
        idempotent=True,
        payload={"body": "Please connect me with a human.", "use_ai": True},
    )
    print("PASS unified support chat and AI fallback")

    request_json("GET", "/dashboard/summary", user_id="user_admin", role="admin")
    request_json("GET", "/dashboard/alerts", user_id="user_admin", role="admin")
    print("PASS dashboard and SLA alert visibility")

    artifact = request_json(
        "POST",
        f"/insurance/claims/{incident['id']}/exports",
        user_id="user_employee",
        role="employee",
    )
    for _attempt in range(20):
        artifact = request_json(
            "GET",
            f"/insurance/exports/{artifact['id']}",
            user_id="user_employee",
            role="employee",
        )
        if artifact["status"] == "ready":
            break
        time.sleep(0.5)
    assert artifact["status"] == "ready", "Export worker did not produce artifact"
    download = request_json(
        "GET",
        f"/insurance/exports/{artifact['id']}/download",
        user_id="user_employee",
        role="employee",
    )
    with urlopen(urljoin(ORIGIN, download["download_url"]), timeout=10) as response:
        assert b"claim_id,customer_id,incident_type,claim_state" in response.read()
    print("PASS expiring private export download")

    expect_http_status(403, "GET", "/insurance/queues", user_id="user_customer", role="customer")
    expect_http_status(
        404,
        "GET",
        f"/insurance/claims/{incident['id']}",
        user_id="user_employee",
        role="employee",
        organization_id="org_other",
    )
    token = issue_storage_download_token(
        organization_id="org_demo",
        storage_key="org_demo/expired.csv",
        expires_seconds=-1,
    )
    expect_http_status(
        401,
        "GET",
        f"/insurance/exports/downloads/content?{urlencode({'token': token})}",
        user_id="user_employee",
        role="employee",
    )
    print("PASS production-readiness smoke suite")


if __name__ == "__main__":
    main()
