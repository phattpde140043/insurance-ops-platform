import {
  getDashboardCharts,
  getDashboardSummary,
  getSlaAlerts,
  type ChartSeries,
  type SlaAlert
} from "../lib/dashboard-api";

function maxValue(series: ChartSeries) {
  return Math.max(...series.data.map((point) => point.value), 1);
}

export default async function DashboardPage() {
  try {
    const [summary, charts, alerts] = await Promise.all([
      getDashboardSummary(),
      getDashboardCharts(),
      getSlaAlerts()
    ]);

    return (
      <div className="stack">
        <section className="page-header">
          <div>
            <h2>Dashboard</h2>
            <p>
              Operational metrics, workflow distribution and active SLA alerts
              from persisted tenant data.
            </p>
          </div>
        </section>

        <section className="grid">
          {summary.cards.map((metric) => (
            <article className="card" key={metric.label}>
              <h3>{metric.label}</h3>
              <p className="metric">{metric.value}</p>
            </article>
          ))}
        </section>

        <section className="grid two">
          {charts.map((series) => (
            <article className="panel" key={series.key}>
              <h3>{series.label}</h3>
              {series.data.length === 0 ? (
                <p className="muted">No data yet.</p>
              ) : (
                <div className="bar-chart">
                  {series.data.map((point) => (
                    <div className="bar-row" key={point.label}>
                      <span>{point.label}</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{
                            width: `${(point.value / maxValue(series)) * 100}%`
                          }}
                        />
                      </div>
                      <strong>{point.value}</strong>
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </section>

        <section className="panel">
          <h3>SLA alerts</h3>
          {alerts.length === 0 ? (
            <p className="muted">No active SLA alerts.</p>
          ) : (
            <AlertTable alerts={alerts} />
          )}
        </section>
      </div>
    );
  } catch (error) {
    return (
      <div className="stack">
        <section className="page-header">
          <div>
            <h2>Dashboard unavailable</h2>
            <p>Metrics could not be loaded from the backend.</p>
          </div>
        </section>
        <section className="panel error-panel">
          <h3>Request failed</h3>
          <p className="muted">
            {error instanceof Error ? error.message : "Unknown dashboard error"}
          </p>
        </section>
      </div>
    );
  }
}

function AlertTable({ alerts }: { alerts: SlaAlert[] }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Target</th>
          <th>Severity</th>
          <th>Status</th>
          <th>Breached</th>
        </tr>
      </thead>
      <tbody>
        {alerts.map((alert) => (
          <tr key={alert.id}>
            <td>
              {alert.target_type}:{alert.target_id}
            </td>
            <td>{alert.severity}</td>
            <td><span className="status">{alert.status}</span></td>
            <td>{alert.breached_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
