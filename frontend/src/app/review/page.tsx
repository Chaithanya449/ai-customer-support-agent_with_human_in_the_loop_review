"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";

type QueueRecord = {
  request_id: number;
  order_id: number;
  requested_at: string;
  first_name: string;
  last_name: string;
  email: string;
  order_status: string;
  order_item_id?: number;
  quantity?: number;
  unit_price?: number;
  product_name?: string;
  reason_text?: string;
  amount?: number;
};
type QueueItem = QueueRecord & { kind: "returns" | "refunds"; key: string };
type QueueResponse = { returns: QueueRecord[]; refunds: QueueRecord[] };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function ReviewPanel() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const selected = items.find((item) => item.key === selectedKey) ?? items[0];

  async function loadQueue() {
    setError("");
    try {
      const response = await fetch(`${API_URL}/review/queue`, { cache: "no-store" });
      const body = (await response.json()) as QueueResponse | { detail?: string };
      if (!response.ok) throw new Error("detail" in body ? body.detail : "Could not load the review queue.");
      const data = body as QueueResponse;
      const queue: QueueItem[] = [
        ...data.refunds.map((row) => ({ ...row, kind: "refunds" as const, key: `F-${row.request_id}` })),
        ...data.returns.map((row) => ({ ...row, kind: "returns" as const, key: `R-${row.request_id}` })),
      ];
      setItems(queue);
      setSelectedKey((current) => queue.some((item) => item.key === current) ? current : queue[0]?.key ?? "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load the review queue.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadQueue();
  }, []);

  async function decide(decision: "approve" | "reject") {
    if (!selected || working) return;
    setWorking(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API_URL}/review/${selected.kind}/${selected.request_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, note }),
      });
      const body = (await response.json()) as { message?: string; detail?: string };
      if (!response.ok) throw new Error(body.detail ?? "Could not save the review decision.");
      setNotice(body.message ?? `Request ${decision}d.`);
      setNote("");
      await loadQueue();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save the review decision.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="review-page">
      <aside className="review-queue">
        <div className="queue-title"><h1>Review queue</h1><span>{items.length} pending</span></div>
        {loading && <p className="queue-message">Loading pending requests…</p>}
        {!loading && !error && items.length === 0 && <p className="queue-message">No requests are waiting for review.</p>}
        {items.map((item) => (
          <button className={`queue-item ${selected?.key === item.key ? "selected" : ""}`} key={item.key} onClick={() => { setSelectedKey(item.key); setNote(""); setNotice(""); }}>
            <strong>{item.kind === "refunds" ? "REF" : "RET"}-{item.request_id} · {item.kind === "refunds" ? "Refund" : "Return"}</strong>
            <span>Order {item.order_id} · {item.first_name} {item.last_name}</span>
            <small>{item.kind === "refunds" ? `Amount $${(item.amount ?? 0).toFixed(2)}` : `${item.product_name} · ${item.reason_text}`}</small>
          </button>
        ))}
        {error && <p className="queue-error">{error}</p>}
      </aside>

      <section className="review-detail">
        <header><Link href="/">← Customer support</Link><span>Human review</span></header>
        {!selected ? (
          <div className="review-empty"><h2>{loading ? "Loading review queue…" : "All caught up"}</h2><p>{loading ? "" : "There are no pending refund or return requests."}</p></div>
        ) : (
          <>
            <h2>{selected.kind === "refunds" ? "REF" : "RET"}-{selected.request_id} · {selected.kind === "refunds" ? "Refund request" : "Return request"}</h2>
            <div className="review-card">
              <strong>Request details</strong>
              <p>Order {selected.order_id} · {selected.first_name} {selected.last_name} · {selected.email}</p>
              {selected.kind === "returns" ? (
                <p>{selected.product_name} · quantity {selected.quantity} · reason: {selected.reason_text} · ${((selected.unit_price ?? 0) * (selected.quantity ?? 0)).toFixed(2)} item value</p>
              ) : <p>Refund amount requested: ${(selected.amount ?? 0).toFixed(2)}</p>}
              <p className="review-meta">Order status: {selected.order_status} · Submitted: {selected.requested_at}</p>
            </div>
            <div className="review-warning">
              <strong>Human decision required</strong>
              <p>Review the request details before approving or rejecting it. Approval may change payment and order status.</p>
            </div>
            <div className="review-card draft-card">
              <label htmlFor="review-note">Reviewer note (optional)</label>
              <textarea id="review-note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add a note to keep with this decision…" maxLength={1000} />
            </div>
            {notice && <div className="review-notice" role="status">{notice}</div>}
            {error && <div className="review-error" role="alert">{error}</div>}
            <div className="review-actions">
              <button className="approve" disabled={working} onClick={() => void decide("approve")}>{working ? "Saving…" : "Approve"}</button>
              <button className="reject" disabled={working} onClick={() => void decide("reject")}>Reject</button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

export default dynamic(() => Promise.resolve(ReviewPanel), { ssr: false });
