"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import {
  requestPortalAppointment,
  startPortalConversation
} from "../lib/portal-api";

export function PortalActions() {
  const router = useRouter();
  const [appointmentStatus, setAppointmentStatus] = useState("");
  const [conversationStatus, setConversationStatus] = useState("");

  async function submitAppointment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setAppointmentStatus("Requesting...");
    try {
      await requestPortalAppointment(String(form.get("scheduled_at")));
      setAppointmentStatus("Appointment requested");
      event.currentTarget.reset();
    } catch {
      setAppointmentStatus("Could not request appointment");
    }
  }

  async function submitConversation() {
    setConversationStatus("Starting...");
    try {
      const conversation = await startPortalConversation();
      setConversationStatus("Conversation started");
      router.push(`/ai?conversationId=${conversation.id}`);
    } catch {
      setConversationStatus("Could not start conversation");
    }
  }

  return (
    <section className="grid two">
      <form className="panel form-grid" onSubmit={submitAppointment}>
        <h3>Request appointment</h3>
        <input
          name="scheduled_at"
          placeholder="2026-06-01T10:00:00Z"
          required
        />
        <button className="button" type="submit">
          Request
        </button>
        <p className="muted">{appointmentStatus}</p>
      </form>
      <article className="panel form-grid">
        <h3>Start support conversation</h3>
        <button className="button" type="button" onClick={submitConversation}>
          Start conversation
        </button>
        <p className="muted">{conversationStatus}</p>
      </article>
    </section>
  );
}
