import {
  getPortalIncidents,
  getPortalPolicies,
  getPortalSummary
} from "../lib/portal-api";
import { PortalActions } from "./portal-actions";

export default async function PortalPage() {
  try {
    const [summary, policies, incidents] = await Promise.all([
      getPortalSummary(),
      getPortalPolicies(),
      getPortalIncidents()
    ]);

    return (
      <div className="stack">
        <section className="page-header">
          <div>
            <p className="eyebrow">Customer portal</p>
            <h2>{summary.customer.name}</h2>
            <p>
              Review active coverage, recent incidents, upcoming appointments
              and open support conversations linked to your customer profile.
            </p>
          </div>
        </section>

        <section className="grid">
          <article className="card">
            <h3>Policies</h3>
            <p className="metric">{summary.policies.length}</p>
            <p className="muted">Active and recent policies</p>
          </article>
          <article className="card">
            <h3>Incidents</h3>
            <p className="metric">{summary.recent_incidents.length}</p>
            <p className="muted">Recent claim activity</p>
          </article>
          <article className="card">
            <h3>Support</h3>
            <p className="metric">{summary.open_conversations.length}</p>
            <p className="muted">Open conversations</p>
          </article>
        </section>

        <section className="grid two">
          <article className="panel">
            <h3>Policy history</h3>
            {policies.length === 0 ? (
              <p className="muted">No policies are linked to this customer.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Policy</th>
                    <th>Plan</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {policies.map((policy) => (
                    <tr key={policy.id}>
                      <td>{policy.id}</td>
                      <td>{policy.plan_id}</td>
                      <td>
                        <span className="status">{policy.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>

          <article className="panel">
            <h3>Incident history</h3>
            {incidents.length === 0 ? (
              <p className="muted">No incidents have been reported.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Type</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <tr key={incident.id}>
                      <td>{incident.id}</td>
                      <td>{incident.incident_type}</td>
                      <td>
                        <span className="status">{incident.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>
        </section>

        <section className="grid two">
          <article className="panel">
            <h3>Upcoming appointments</h3>
            {summary.upcoming_appointments.length === 0 ? (
              <p className="muted">No appointments are scheduled.</p>
            ) : (
              <div className="stack">
                {summary.upcoming_appointments.map((appointment) => (
                  <div className="row" key={appointment.id}>
                    <strong>{appointment.scheduled_at}</strong>
                    <span className="status">{appointment.status}</span>
                  </div>
                ))}
              </div>
            )}
          </article>
          <article className="panel">
            <h3>Support conversations</h3>
            {summary.open_conversations.length === 0 ? (
              <p className="muted">No open support conversations.</p>
            ) : (
              <div className="stack">
                {summary.open_conversations.map((conversation) => (
                  <div className="row" key={conversation.id}>
                    <a
                      className="table-link"
                      href={`/ai?conversationId=${conversation.id}`}
                    >
                      {conversation.id}
                    </a>
                    <span className="status">{conversation.status}</span>
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>

        <PortalActions />
      </div>
    );
  } catch (error) {
    return (
      <div className="stack">
        <section className="page-header">
          <div>
            <p className="eyebrow">Customer portal</p>
            <h2>Portal unavailable</h2>
            <p>
              The portal could not load this customer profile. Check that the
              backend is running and that the demo customer is linked.
            </p>
          </div>
        </section>
        <section className="panel error-panel">
          <h3>Request failed</h3>
          <p className="muted">
            {error instanceof Error ? error.message : "Unknown portal error"}
          </p>
        </section>
      </div>
    );
  }
}
