import { MessageComposer } from "./message-composer";
import {
  getSupportConversation,
  getSupportConversations,
  type SupportConversation,
  type SupportConversationDetail
} from "../lib/chat-api";

type AiPageProps = {
  searchParams?: Promise<{ conversationId?: string }>;
};

export default async function AiPage({ searchParams }: AiPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  let conversations: SupportConversation[] = [];
  let activeConversation: SupportConversationDetail | null = null;
  let error = "";

  try {
    conversations = await getSupportConversations();
    const activeId = resolvedSearchParams.conversationId ?? conversations[0]?.id;
    if (activeId) {
      activeConversation = await getSupportConversation(activeId);
    }
  } catch (requestError) {
    error =
      requestError instanceof Error
        ? requestError.message
        : "Could not load conversations";
  }

  return (
    <div className="stack">
      <section className="page-header">
        <div>
          <h2>Support chat</h2>
          <p>
            Continue persisted support conversations with AI answers stored in
            the same thread.
          </p>
        </div>
      </section>

      {error ? (
        <section className="panel error-panel">
          <h3>Request failed</h3>
          <p className="muted">{error}</p>
        </section>
      ) : null}

      <section className="chat-shell">
        <aside className="panel chat-list">
          <h3>Threads</h3>
          {conversations.length === 0 ? (
            <p className="muted">No support conversations are assigned.</p>
          ) : (
            conversations.map((conversation) => (
              <a
                className={
                  activeConversation?.id === conversation.id
                    ? "thread-link active"
                    : "thread-link"
                }
                href={`/ai?conversationId=${conversation.id}`}
                key={conversation.id}
              >
                <strong>{conversation.customer_id}</strong>
                <span>{conversation.status}</span>
              </a>
            ))
          )}
        </aside>

        <section className="panel chat-thread">
          {activeConversation === null ? (
            <p className="muted">Select a support conversation to begin.</p>
          ) : (
            <>
              <div className="thread-header">
                <div>
                  <h3>{activeConversation.customer_id}</h3>
                  <p className="muted">{activeConversation.id}</p>
                </div>
                <span className="status">{activeConversation.status}</span>
              </div>
              {activeConversation.needs_human ? (
                <p className="muted">
                  Employee follow-up requested: {activeConversation.handoff_reason}
                </p>
              ) : null}

              <div className="messages">
                {activeConversation.messages.length === 0 ? (
                  <p className="muted">No messages yet.</p>
                ) : (
                  activeConversation.messages.map((message) => (
                    <article className="message" key={message.id}>
                      <div className="message-meta">
                        <strong>{message.role}</strong>
                        <span>{message.created_at}</span>
                      </div>
                      <p>{message.body}</p>
                      {message.citations.length > 0 ? (
                        <p className="muted">
                          Citations: {message.citations.join(", ")}
                        </p>
                      ) : null}
                    </article>
                  ))
                )}
              </div>

              <MessageComposer conversationId={activeConversation.id} />
            </>
          )}
        </section>
      </section>
    </div>
  );
}
