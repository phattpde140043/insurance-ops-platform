import { adminTasks } from "../lib/demo-data";

export default function AdminPage() {
  return (
    <div className="stack">
      <section className="page-header">
        <div>
          <h2>Admin console</h2>
          <p>
            Centralize user management, role assignment, access history, audit
            events and tenant configuration.
          </p>
        </div>
      </section>
      <section className="grid two">
        {adminTasks.map((task) => (
          <article className="card" key={task}>
            <h3>{task}</h3>
            <p className="muted">Planned in Phase 1 platform core.</p>
          </article>
        ))}
      </section>
    </div>
  );
}

