"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { openClaimConversation, transitionClaim } from "../../../lib/claim-api";

type ClaimActionsProps = {
  claimId: string;
  transitions: string[];
};

export function ClaimActions({ claimId, transitions }: ClaimActionsProps) {
  const router = useRouter();
  const [pendingState, setPendingState] = useState<string | null>(null);
  const [isOpeningConversation, setIsOpeningConversation] = useState(false);
  const [error, setError] = useState("");

  async function submitTransition(toState: string) {
    setPendingState(toState);
    setError("");
    try {
      await transitionClaim(claimId, toState, `Move claim to ${toState}`);
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not update claim"
      );
    } finally {
      setPendingState(null);
    }
  }

  async function openConversation() {
    setIsOpeningConversation(true);
    setError("");
    try {
      const conversation = await openClaimConversation(claimId);
      router.push(`/ai?conversationId=${conversation.id}`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not open support thread"
      );
    } finally {
      setIsOpeningConversation(false);
    }
  }

  return (
    <div className="stack">
      <div className="actions">
        <button
          className="button secondary"
          disabled={isOpeningConversation}
          onClick={() => void openConversation()}
          type="button"
        >
          {isOpeningConversation ? "Opening..." : "Support thread"}
        </button>
        {transitions.map((toState) => (
          <button
            className="button"
            disabled={pendingState !== null}
            key={toState}
            onClick={() => void submitTransition(toState)}
            type="button"
          >
            {pendingState === toState ? "Updating..." : toState}
          </button>
        ))}
      </div>
      {transitions.length === 0 ? (
        <p className="muted">No available transitions for this role.</p>
      ) : null}
      {error ? <p className="muted">{error}</p> : null}
    </div>
  );
}
