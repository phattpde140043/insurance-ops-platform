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


@pytest.mark.integration
def test_insurance_message_ai_fields_exist() -> None:
    columns = Base.metadata.tables["insurance_messages"].columns
    assert "role" in columns
    assert "citations_json" in columns


@pytest.mark.integration
def test_conversation_claim_link_exists() -> None:
    columns = Base.metadata.tables["insurance_conversations"].columns
    assert "claim_id" in columns


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
