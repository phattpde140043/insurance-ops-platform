import { getMyQueue, type QueueItem } from "../lib/queue-api";
import { IncidentForm } from "./incident-form";

export default async function InsurancePage() {
  let queue: QueueItem[] = [];
  let error = "";

  try {
    queue = await getMyQueue();
  } catch (requestError) {
    error =
      requestError instanceof Error
        ? requestError.message
        : "Could not load workload queue";
  }

  return (
    <div className="stack">
      <section className="page-header">
        <div>
          <h2>Insurance operations</h2>
          <p>
            Triage assigned customers, incidents, appointments and support
            conversations from one operational queue.
          </p>
        </div>
        <div className="actions">
          <a className="button secondary" href="/portal">Customer portal</a>
        </div>
      </section>
      <section className="panel">
        <h3>My queue</h3>
        {error ? (
          <p className="muted">{error}</p>
        ) : queue.length === 0 ? (
          <p className="muted">No assigned queue items.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Source</th>
                <th>Customer</th>
                <th>Priority</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((item) => (
                <tr key={item.id}>
                  <td>{item.item_type}</td>
                  <td>
                    {item.item_type === "incident" ? (
                      <a
                        className="table-link"
                        href={`/insurance/claims/${item.source_id}`}
                      >
                        {item.source_id}
                      </a>
                    ) : (
                      item.source_id
                    )}
                  </td>
                  <td>{item.customer_id}</td>
                  <td>{item.priority}</td>
                  <td><span className="status">{item.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section className="panel">
        <h3>Queue filters</h3>
        <div className="actions">
          <button className="button secondary" disabled type="button">
            Status
          </button>
          <button className="button secondary" disabled type="button">
            Priority
          </button>
          <button className="button secondary" disabled type="button">
            Due date
          </button>
        </div>
      </section>
      <section className="panel">
        <h3>Queue detail</h3>
        <p className="muted">
          Selectable queue details and actions are backed by the queue detail
          API and will be connected as the workflow grows.
        </p>
      </section>
      <IncidentForm />
    </div>
  );
}
