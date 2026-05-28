import json
import logging

from fastapi.testclient import TestClient

from app.core.observability import TRACE_ID_HEADER
from app.main import app


def test_health_response_generates_trace_id(caplog) -> None:
    caplog.set_level(logging.INFO, logger="opsbridge.request")
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers[TRACE_ID_HEADER]
    assert any(
        json.loads(record.message)["trace_id"] == response.headers[TRACE_ID_HEADER]
        for record in caplog.records
        if record.name == "opsbridge.request"
    )


def test_health_response_preserves_incoming_trace_id() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/health",
        headers={TRACE_ID_HEADER: "trace-from-client"},
    )

    assert response.status_code == 200
    assert response.headers[TRACE_ID_HEADER] == "trace-from-client"
