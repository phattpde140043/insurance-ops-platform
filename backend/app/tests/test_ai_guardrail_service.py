from app.domains.ai.guardrail_service import SemanticGuardrailService


def test_forbidden_claim_decision_is_blocked() -> None:
    decision = SemanticGuardrailService().check_input(
        "Please approve my claim and authorize payment now."
    )

    assert decision.allowed is False
    assert decision.reason == "forbidden_decision"


def test_citations_must_match_allowed_tenant_chunks() -> None:
    decision = SemanticGuardrailService().check_output(
        answer="Based on the company knowledge base: submit the incident form.",
        citations=["chunk_other"],
        allowed_chunk_ids={"chunk_allowed"},
    )

    assert decision.allowed is False
    assert decision.reason == "citation_mismatch"
