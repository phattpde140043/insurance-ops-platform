import pytest

from app.core.database import Base
import app.models  # noqa: F401


@pytest.mark.integration
def test_metadata_contains_core_tables() -> None:
    expected_tables = {
        "organizations",
        "users",
        "insurance_customers",
        "knowledge_documents",
        "background_jobs",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


@pytest.mark.integration
def test_queue_fields_exist_on_workflow_tables() -> None:
    for table_name in {
        "insurance_employee_assignments",
        "insurance_incident_reports",
        "insurance_appointments",
        "insurance_conversations",
    }:
        columns = Base.metadata.tables[table_name].columns
        assert "priority" in columns
        assert "due_at" in columns


@pytest.mark.integration
def test_claim_lifecycle_persistence_exists() -> None:
    incident_columns = Base.metadata.tables["insurance_incident_reports"].columns
    assert "claim_state" in incident_columns

    transition_columns = Base.metadata.tables["insurance_claim_transitions"].columns
    for column_name in {
        "organization_id",
        "claim_id",
        "actor_user_id",
        "from_state",
        "to_state",
        "reason",
        "created_at",
    }:
        assert column_name in transition_columns

    correction_columns = Base.metadata.tables["insurance_claim_corrections"].columns
    for column_name in {
        "organization_id",
        "claim_id",
        "reviewer_user_id",
        "status",
        "corrected_fields",
        "changed_fields",
        "approved_by_user_id",
        "approved_at",
    }:
        assert column_name in correction_columns


@pytest.mark.integration
def test_insurance_message_ai_fields_exist() -> None:
    columns = Base.metadata.tables["insurance_messages"].columns
    assert "role" in columns
    assert "citations_json" in columns


@pytest.mark.integration
def test_conversation_claim_link_exists() -> None:
    columns = Base.metadata.tables["insurance_conversations"].columns
    assert "claim_id" in columns
    assert "needs_human" in columns
    assert "handoff_reason" in columns


@pytest.mark.integration
def test_sla_persistence_exists() -> None:
    assert "sla_rules" in Base.metadata.tables
    assert "sla_alerts" in Base.metadata.tables

    rule_columns = Base.metadata.tables["sla_rules"].columns
    for column_name in {"organization_id", "target_type", "threshold_minutes", "status"}:
        assert column_name in rule_columns

    alert_columns = Base.metadata.tables["sla_alerts"].columns
    for column_name in {
        "organization_id",
        "rule_id",
        "target_type",
        "target_id",
        "status",
        "breached_at",
        "resolved_at",
    }:
        assert column_name in alert_columns


@pytest.mark.integration
def test_background_job_claiming_fields_exist() -> None:
    columns = Base.metadata.tables["background_jobs"].columns
    for column_name in {
        "status",
        "attempts",
        "available_at",
        "locked_by",
        "locked_until",
        "started_at",
        "finished_at",
        "error_message",
    }:
        assert column_name in columns


@pytest.mark.integration
def test_file_asset_checksum_exists() -> None:
    columns = Base.metadata.tables["file_assets"].columns
    assert "checksum_sha256" in columns


@pytest.mark.integration
def test_export_artifact_persistence_exists() -> None:
    columns = Base.metadata.tables["export_artifacts"].columns
    for column_name in {
        "organization_id",
        "artifact_type",
        "resource_type",
        "resource_id",
        "status",
        "file_asset_id",
        "requested_by_user_id",
    }:
        assert column_name in columns


@pytest.mark.integration
def test_domain_outbox_persistence_exists() -> None:
    columns = Base.metadata.tables["domain_outbox_events"].columns
    for column_name in {
        "organization_id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "producer_module",
        "payload_json",
        "idempotency_key",
        "status",
        "attempts",
        "available_at",
        "locked_by",
        "locked_until",
        "published_at",
        "error_message",
    }:
        assert column_name in columns


@pytest.mark.integration
def test_dashboard_read_model_persistence_exists() -> None:
    assert "dashboard_metric_projections" in Base.metadata.tables
    assert "dashboard_sla_target_projections" in Base.metadata.tables
    assert "dashboard_projection_events" in Base.metadata.tables

    metric_columns = Base.metadata.tables["dashboard_metric_projections"].columns
    for column_name in {"organization_id", "metric_key", "dimension", "time_bucket", "value"}:
        assert column_name in metric_columns

    target_columns = Base.metadata.tables["dashboard_sla_target_projections"].columns
    for column_name in {"organization_id", "target_type", "target_id", "status", "due_at", "last_event_id"}:
        assert column_name in target_columns


@pytest.mark.integration
def test_idempotency_record_persistence_exists() -> None:
    columns = Base.metadata.tables["idempotency_records"].columns
    for column_name in {
        "organization_id",
        "actor_user_id",
        "command_name",
        "idempotency_key",
        "request_fingerprint",
        "status",
        "resource_type",
        "resource_id",
        "response_metadata",
    }:
        assert column_name in columns


@pytest.mark.integration
def test_ai_rate_limit_window_persistence_exists() -> None:
    columns = Base.metadata.tables["ai_rate_limit_windows"].columns
    for column_name in {
        "organization_id",
        "subject_type",
        "subject_id",
        "capability",
        "window_started_at",
        "request_count",
    }:
        assert column_name in columns
