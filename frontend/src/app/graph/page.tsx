import Link from "next/link";

const tools = [
  { name: "check_order_status", detail: "Reads order, status, items and shipment details." },
  { name: "lookup_return_policy", detail: "Reads return reasons and explains the policy." },
  { name: "process_return_request", detail: "Validates and records a customer-confirmed return." },
  { name: "request_refund", detail: "Creates a refund request for human review." },
  { name: "check_refund_status", detail: "Reads return and refund decisions." },
];

function Arrow({ label }: { label?: string }) {
  return <div className="graph-arrow" aria-hidden="true"><span>{label}</span><i /></div>;
}

export default function GraphPage() {
  return (
    <main className="graph-page">
      <header className="graph-header">
        <Link className="store-brand" href="/" aria-label="Back to Store Support">
          <span className="store-mark" aria-hidden="true" />
          <strong>Store Support</strong>
        </Link>
        <nav className="graph-nav" aria-label="Main navigation">
          <Link href="/">Customer chat</Link>
          <Link href="/review">Review queue</Link>
          <span aria-current="page">Agent graph</span>
        </nav>
      </header>

      <section className="graph-content">
        <div className="graph-heading">
          <div>
            <p className="graph-eyebrow">LANGGRAPH · REACT WORKFLOW</p>
            <h1>How the support agent works</h1>
            <p>Each message enters the assistant. It can answer directly or call a database tool, then continue until it has a reply.</p>
          </div>
          <div className="graph-legend"><i /> Agent step <i className="legend-tool" /> Tool or data step</div>
        </div>

        <div className="graph-board" aria-label="LangGraph workflow: customer message flows to the assistant, which either answers or calls tools and loops back before responding">
          <div className="graph-start"><span className="graph-dot" /> Customer message <small>Chat UI → FastAPI</small></div>
          <Arrow />
          <article className="graph-node assistant-node">
            <div className="node-top"><span className="node-icon">✦</span><span className="node-tag">AGENT NODE</span></div>
            <h2>assistant</h2>
            <p>Groq LLM reads the conversation and decides whether to answer or use a tool.</p>
            <div className="node-foot">ChatGroq · tool-bound</div>
          </article>

          <div className="graph-branches">
            <div className="branch branch-answer">
              <div className="branch-label">No tool needed</div>
              <Arrow label="end" />
              <div className="graph-end">✦ <span>Reply to customer</span></div>
            </div>
            <div className="branch branch-tools">
              <div className="branch-label">Tool call requested</div>
              <Arrow label="tools_condition" />
              <article className="graph-node tools-node">
                <div className="node-top"><span className="node-icon tool-icon">⌘</span><span className="node-tag">TOOL NODE</span></div>
                <h2>tools</h2>
                <p>ToolNode runs the selected function. Results are added to conversation state.</p>
                <div className="tool-list">
                  {tools.map((tool) => <div className="tool-row" key={tool.name}><code>{tool.name}</code><span>{tool.detail}</span></div>)}
                </div>
              </article>
              <Arrow label="tool result" />
              <div className="loop-back"><span>↶</span><div><strong>Back to assistant</strong><small>Interpret result · reply or call another tool</small></div></div>
            </div>
          </div>

          <div className="graph-storage">
            <div className="storage-line" />
            <div className="storage-card"><span className="storage-icon">▤</span><div><strong>SQLite · ecommerce.db</strong><small>Orders, products, shipments, returns and payments</small></div><span className="storage-kind">DATA</span></div>
            <div className="storage-card checkpoint-card"><span className="storage-icon">◷</span><div><strong>SQLite · checkpoints.db</strong><small>Conversation state saved by LangGraph</small></div><span className="storage-kind">MEMORY</span></div>
          </div>
        </div>

        <aside className="human-review">
          <div className="review-step">HUMAN REVIEW · SEPARATE PATH</div>
          <div className="review-flow"><strong>Pending request</strong><span>→</span><strong>Reviewer queue</strong><span>→</span><strong>Approve or reject</strong><span>→</span><strong>Record decision / refund</strong></div>
          <p>Refund requests and return decisions are handled by a person in the review panel. The chat agent can request review; it does not approve requests itself.</p>
          <Link href="/review">Open review queue <span aria-hidden="true">↗</span></Link>
        </aside>
        <footer className="graph-caption">Graph reflects the current implementation in <code>agent.py</code>, <code>tools.py</code> and <code>api.py</code>.</footer>
      </section>
    </main>
  );
}
