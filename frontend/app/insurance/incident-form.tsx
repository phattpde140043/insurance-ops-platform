"use client";

import { FormEvent, useState } from "react";
import { apiPost } from "../lib/api-client";

export function IncidentForm() {
  const [status, setStatus] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setStatus("Reporting...");
    try {
      await apiPost("/insurance/incidents", {
        customer_id: String(form.get("customer_id")),
        incident_type: String(form.get("incident_type")),
        description: String(form.get("description"))
      });
      setStatus("Incident reported");
      event.currentTarget.reset();
    } catch {
      setStatus("Could not report incident");
    }
  }

  return (
    <form className="panel form-grid" onSubmit={submit}>
      <h3>Report incident</h3>
      <input name="customer_id" placeholder="customer_lan" required />
      <input name="incident_type" defaultValue="medical" required />
      <textarea name="description" placeholder="Describe the incident" required />
      <button className="button" type="submit">Report</button>
      <p className="muted">{status}</p>
    </form>
  );
}

