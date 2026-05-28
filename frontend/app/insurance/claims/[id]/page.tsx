import { ClaimActions } from "./claim-actions";
import {
  getClaimDetail,
  getClaimHistory,
  type ClaimDetail,
  type ClaimTransition
} from "../../../lib/claim-api";

type ClaimPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ClaimPage({ params }: ClaimPageProps) {
  const { id } = await params;
  let claim: ClaimDetail | null = null;
  let history: ClaimTransition[] = [];
  let error = "";

  try {
    [claim, history] = await Promise.all([
      getClaimDetail(id),
      getClaimHistory(id)
    ]);
  } catch (requestError) {
    error =
      requestError instanceof Error
        ? requestError.message
        : "Could not load claim";
  }

  if (error || claim === null) {
    return (
      <div className="stack">
        <section className="page-header">
          <div>
            <h2>Claim detail</h2>
            <p>Claim information could not be loaded.</p>
          </div>
          <a className="button secondary" href="/insurance">Back to queue</a>
        </section>
        <section className="panel error-panel">
          <h3>Request failed</h3>
          <p className="muted">{error}</p>
        </section>
      </div>
    );
  }

  return (
    <div className="stack">
      <section className="page-header">
        <div>
          <h2>Claim {claim.id}</h2>
          <p>{claim.description}</p>
        </div>
        <div className="actions">
          <a className="button secondary" href="/insurance">Back to queue</a>
        </div>
      </section>

      <section className="grid">
        <div className="card">
          <h3>State</h3>
          <p className="metric">{claim.claim_state}</p>
        </div>
        <div className="card">
          <h3>Customer</h3>
          <p className="metric">{claim.customer_id}</p>
        </div>
        <div className="card">
          <h3>Type</h3>
          <p className="metric">{claim.incident_type}</p>
        </div>
      </section>

      <section className="panel">
        <h3>Available actions</h3>
        <ClaimActions
          claimId={claim.id}
          transitions={claim.allowed_transitions}
        />
      </section>

      <section className="panel">
        <h3>Timeline</h3>
        {history.length === 0 ? (
          <p className="muted">No transitions recorded yet.</p>
        ) : (
          <div className="timeline">
            {history.map((item) => (
              <div className="timeline-item" key={item.id}>
                <div>
                  <strong>
                    {item.from_state ?? "created"} to {item.to_state}
                  </strong>
                  <p className="muted">{item.reason}</p>
                </div>
                <span className="muted">{item.created_at}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
