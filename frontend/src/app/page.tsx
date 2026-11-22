"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";

type Message = { role: "assistant" | "user"; content: string; id: number };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function SupportChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [conversationId, setConversationId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const nextId = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function sendMessage(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    const userId = nextId.current++;
    setMessages((items) => [
      ...items,
      { role: "user", content: message, id: userId },
    ]);
    setDraft("");
    setError("");
    setBusy(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, conversation_id: conversationId }),
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "Unable to reach support. Please try again.");
      }
      const body = (await response.json()) as { conversation_id: string; reply: string };
      setConversationId(body.conversation_id);
      setMessages((items) => [
        ...items,
        { role: "assistant", content: body.reply, id: nextId.current++ },
      ]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(draft);
  }

  function keyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      void sendMessage(draft);
    }
  }

  function reset() {
    setMessages([]);
    setConversationId(undefined);
    setError("");
    setDraft("");
    inputRef.current?.focus();
  }

  return (
    <main className="support-app">
      <header className="support-header">
        <Link className="store-brand" href="/" aria-label="Store support home">
          <span className="store-mark" aria-hidden="true" />
          <strong>Store Support</strong>
        </Link>
        <div className="agent-status"><i /> Agent online</div>
      </header>

      <section className="chat-scroll" aria-label="Support conversation">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-mark">?</div>
            <h1>How can we help?</h1>
            <p>Ask about an order, a return, or our return policy.</p>
            <div className="quick-prompts">
              <button onClick={() => void sendMessage("Can you check the status of my order?")}>Check an order</button>
              <button onClick={() => void sendMessage("What is your return policy?")}>Return policy</button>
              <button onClick={() => void sendMessage("I would like to return an item.")}>Start a return</button>
            </div>
            <p className="numeric-note">Orders use numeric IDs. Include your order ID when you ask about an order.</p>
          </div>
        ) : (
          <div className="chat-thread">
            {messages.map((message) => message.role === "user" ? (
              <div className="user-line" key={message.id}><div className="user-bubble">{message.content}</div></div>
            ) : (
              <article className="assistant-line" key={message.id}>
                <div className="tool-caption">Support agent</div>
                <div className="assistant-bubble">{message.content}</div>
                <div className="feedback" aria-label="Rate this response">
                  <button aria-label="Helpful" title="Helpful">♧</button>
                  <button aria-label="Not helpful" title="Not helpful">♧</button>
                </div>
              </article>
            ))}
            {busy && <div className="assistant-line"><div className="tool-caption">Support agent</div><div className="assistant-bubble loading-dots"><i /><i /><i /></div></div>}
            <div ref={bottomRef} />
          </div>
        )}
      </section>

      <footer className="composer-dock">
        {error && <div className="request-error" role="alert">{error}</div>}
        <form className="message-form" onSubmit={submit}>
          <input
            ref={inputRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={keyDown}
            placeholder="Type your message"
            maxLength={4000}
            aria-label="Type your message"
            disabled={busy}
          />
          <button type="submit" disabled={!draft.trim() || busy}>Send</button>
        </form>
        {messages.length > 0 && <button className="reset-link" onClick={reset}>Start a new conversation</button>}
      </footer>
    </main>
  );
}

export default dynamic(() => Promise.resolve(SupportChat), { ssr: false });
