from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    reason: str | None = None


SAFE_FALLBACK = (
    "I cannot make claim, coverage or payment decisions. "
    "Please contact a support employee for help."
)


class SemanticGuardrailService:
    def check_input(self, message: str) -> GuardrailDecision:
        normalized = message.strip().lower()
        checks = {
            "prompt_injection": (
                "ignore previous",
                "ignore all instructions",
                "system prompt",
                "reveal your prompt",
                "developer message",
            ),
            "cross_tenant_request": (
                "another tenant",
                "other tenant",
                "different organization",
                "all customers",
            ),
            "forbidden_decision": (
                "approve my claim",
                "reject my claim",
                "decide my claim",
                "guarantee coverage",
                "authorize payment",
                "decide coverage",
            ),
        }
        for reason, patterns in checks.items():
            if any(pattern in normalized for pattern in patterns):
                return GuardrailDecision(allowed=False, reason=reason)
        return GuardrailDecision(allowed=True)

    def check_output(
        self, *, answer: str, citations: list[str], allowed_chunk_ids: set[str]
    ) -> GuardrailDecision:
        normalized = answer.lower()
        unsafe_commitments = (
            "your claim is approved",
            "your claim is rejected",
            "coverage is guaranteed",
            "payment is authorized",
        )
        if any(commitment in normalized for commitment in unsafe_commitments):
            return GuardrailDecision(allowed=False, reason="unsupported_commitment")
        if citations and not set(citations).issubset(allowed_chunk_ids):
            return GuardrailDecision(allowed=False, reason="citation_mismatch")
        if allowed_chunk_ids and not citations:
            return GuardrailDecision(allowed=False, reason="missing_citations")
        return GuardrailDecision(allowed=True)
