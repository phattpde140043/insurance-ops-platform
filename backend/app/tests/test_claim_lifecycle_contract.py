ALLOWED_TRANSITIONS = {
    ("reported", "triage", "employee"),
    ("reported", "triage", "admin"),
    ("triage", "in_review", "employee"),
    ("triage", "in_review", "admin"),
    ("in_review", "approved", "employee"),
    ("in_review", "approved", "admin"),
    ("in_review", "rejected", "employee"),
    ("in_review", "rejected", "admin"),
    ("approved", "closed", "employee"),
    ("approved", "closed", "admin"),
    ("rejected", "reopened", "admin"),
    ("closed", "reopened", "admin"),
    ("reopened", "triage", "employee"),
    ("reopened", "triage", "admin"),
}


def transition_allowed(from_state: str, to_state: str, role: str) -> bool:
    return (from_state, to_state, role) in ALLOWED_TRANSITIONS


def test_claim_lifecycle_contract_allows_documented_transition() -> None:
    assert transition_allowed("reported", "triage", "employee")


def test_claim_lifecycle_contract_blocks_customer_transition() -> None:
    assert not transition_allowed("reported", "triage", "customer")


def test_claim_lifecycle_contract_blocks_invalid_transition() -> None:
    assert not transition_allowed("closed", "approved", "admin")


def test_claim_lifecycle_service_must_match_contract() -> None:
    from app.domains.insurance.claim_lifecycle_service import ClaimLifecycleService

    service = ClaimLifecycleService()
    assert service.can_transition("reported", "triage", "employee")
    assert not service.can_transition("closed", "approved", "admin")
