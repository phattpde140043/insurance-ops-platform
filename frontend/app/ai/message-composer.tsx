"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { sendSupportMessage } from "../lib/chat-api";

type MessageComposerProps = {
  conversationId: string;
};

export function MessageComposer({ conversationId }: MessageComposerProps) {
  const router = useRouter();
  const [body, setBody] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState("");

  async function submitMessage() {
    const nextBody = body.trim();
    if (!nextBody) {
      return;
    }
    setIsPending(true);
    setError("");
    try {
      await sendSupportMessage(conversationId, nextBody, true);
      setBody("");
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not send message"
      );
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="composer">
      <textarea
        aria-label="Message"
        onChange={(event) => setBody(event.target.value)}
        placeholder="Ask for help with this support thread"
        value={body}
      />
      <div className="actions">
        <button
          className="button"
          disabled={isPending || body.trim().length === 0}
          onClick={() => void submitMessage()}
          type="button"
        >
          {isPending ? "Sending..." : "Send with AI"}
        </button>
      </div>
      {error ? <p className="muted">{error}</p> : null}
    </div>
  );
}
