"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  approveClaimCorrection,
  saveClaimCorrection,
  type ClaimCorrection
} from "../../../lib/claim-api";

type CorrectionActionsProps = {
  claimId: string;
  incidentType: string;
  corrections: ClaimCorrection[];
};

export function CorrectionActions({
  claimId,
  incidentType,
  corrections
}: CorrectionActionsProps) {
  const router = useRouter();
  const [typeValue, setTypeValue] = useState(incidentType);
  const [priority, setPriority] = useState("normal");
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");

  async function saveDraft() {
    setPending("save");
    setError("");
    try {
      await saveClaimCorrection(claimId, {
        incident_type: typeValue,
        priority
      });
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not save correction");
    } finally {
      setPending("");
    }
  }

  async function approve(correctionId: string) {
    setPending(correctionId);
    setError("");
    try {
      await approveClaimCorrection(claimId, correctionId);
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not approve correction");
    } finally {
      setPending("");
    }
  }

  return (
    <div className="stack">
      <div className="actions">
        <label>
          Type
          <input value={typeValue} onChange={(event) => setTypeValue(event.target.value)} />
        </label>
        <label>
          Priority
          <select value={priority} onChange={(event) => setPriority(event.target.value)}>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </label>
        <button className="button" disabled={pending !== ""} onClick={() => void saveDraft()} type="button">
          {pending === "save" ? "Saving..." : "Save draft"}
        </button>
      </div>
      {corrections.length === 0 ? (
        <p className="muted">No reviewer corrections recorded.</p>
      ) : (
        <div className="timeline">
          {corrections.map((correction) => (
            <div className="timeline-item" key={correction.id}>
              <div>
                <strong>{correction.status}</strong>
                <p className="muted">{correction.changed_fields.join(", ")}</p>
              </div>
              {correction.status === "draft" ? (
                <button className="button secondary" disabled={pending !== ""} onClick={() => void approve(correction.id)} type="button">
                  {pending === correction.id ? "Approving..." : "Approve"}
                </button>
              ) : (
                <span className="muted">{correction.approved_at}</span>
              )}
            </div>
          ))}
        </div>
      )}
      {error ? <p className="muted">{error}</p> : null}
    </div>
  );
}
