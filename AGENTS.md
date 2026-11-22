# Project Context: AI Customer Service Agent (LangGraph + SQLite)

## Goal
Build an AI customer support agent for an **e-commerce store** using **LangGraph** (ReAct pattern).
The agent answers order questions and creates return requests by calling tools that query a **real SQLite database** (no simulated dictionaries).
Note: the notebook's story ("BigCompany Inc.", electronics store) is only a teaching example. Our data is a generic e-commerce dataset, so do not assume any product category or company name.
This is a portfolio project for an **AI Engineer** role. Phase 1 (now) follows the notebook's approach; more intermediate/advanced features come later.

## Database decision
PostgreSQL was **dropped for now** (local server setup was taking too much time). We use **SQLite** (built into Python, one file, no server, no password).
Keep all database code inside the `run_query` helper and the tools, so moving to PostgreSQL later only changes those places.

## Base reference
Starting point is the notebook `028-1st-top-use-case-langgraph-2026.ipynb`:
- `MessagesState`, `assistant` node (LLM with `bind_tools`), `ToolNode`, `tools_condition`, checkpointer, `chat()` helper.
- LLM: the notebook uses `ChatOpenAI`; we use **Groq (free tier)** instead via `langchain-groq`:
  `ChatGroq(model="llama-3.3-70b-versatile", temperature=0)` (alternative: `openai/gpt-oss-120b`).
  The rest of the graph (`bind_tools`, `ToolNode`, `tools_condition`) stays the same.
- Groq's free tier is rate-limited (requests/tokens per minute and per day, per organization), so keep prompts short and handle rate-limit errors gracefully.
- The notebook's dict-based `ORDERS_DB` and tools are being **replaced** by SQL-backed tools.

## Tech stack
Python, LangGraph, langchain-groq (Groq LLM), langchain-core, SQLite (`sqlite3`, built in), pandas (one-time CSV load), python-dotenv, langgraph-checkpoint-sqlite.

## Config (never hardcode secrets)
`.env` holds only `GROQ_API_KEY`. Never print or commit `.env`.
Database file: `ecommerce.db` in the project folder (path kept in one constant, `DB_PATH`).
Add `.env`, `ecommerce.db` and `checkpoints.db` to `.gitignore`.

## Database schema (SQLite, file `ecommerce.db`, built from the dataset CSVs)
Tables are loaded from CSV files with `pandas.DataFrame.to_sql` (one table per CSV, table name = file name). Because of this:
- Types are SQLite types (INTEGER, REAL, TEXT). There are no declared PRIMARY KEY, UNIQUE, FOREIGN KEY or NUMERIC constraints. The columns below still describe the logical keys and relations.
- Timestamps are stored as TEXT in ISO format (`YYYY-MM-DD HH:MM:SS`). Check this after loading. Use SQLite date functions (`julianday`, `datetime`) for date maths.
- Money columns are stored as REAL. Round when displaying (`ROUND(x, 2)` or Python formatting).
- Booleans (`is_active`) are stored as 0/1.

Logical schema:

- **users**(id PK, created_at, email UNIQUE, first_name, last_name, password_hash, phone, updated_at) — 70 rows
- **products**(id PK, brand_id, category_id, compare_at_price NULLABLE, created_at, description, is_active BOOLEAN, name, price, sku UNIQUE, slug UNIQUE) — 400 rows
- **return_reasons**(id PK, reason_text) — 6 rows: 1 Does not fit, 2 Not as described, 3 Arrived too late, 4 Arrived damaged, 5 Changed my mind, 6 Wrong item sent
- **order_statuses**(id PK, description, status_name) — 6 rows: shipped, paid, pending, delivered, refunded, cancelled
- **orders**(id PK, billing_address_id, coupon_id NULLABLE, created_at, discount_amount, order_status_id FK→order_statuses, shipping_address_id, shipping_cost, shipping_method_id, subtotal, tax_amount, total, user_id FK→users) — 360 rows
- **order_items**(id PK, discount_amount, order_id FK→orders, product_id FK→products, quantity, tax_amount, unit_price) — 1000 rows
- **order_returns**(id PK, order_item_id FK→order_items, processed_at NULLABLE, quantity, reason_id FK→return_reasons, requested_at, status) — 20 rows; status values: requested, approved, rejected, refunded
- **shipments**(id PK, delivered_at, order_id FK→orders, shipped_at, tracking_number UNIQUE) — 340 rows
- **payments**(id PK, amount, order_id FK→orders, payment_method_id, processed_at, status, transaction_reference UNIQUE) — 350 rows; status values: completed, failed, refunded

Order IDs are integers (not "ORD-1001"). Data spans roughly 2021–2026, so most delivered orders are outside a 30-day return window.

## Pending schema fix (needed before inserting returns)
SQLite cannot use `ALTER COLUMN`. Recreate `order_returns` so `id` auto-increments and `processed_at` allows NULL:
```sql
CREATE TABLE order_returns_new (
    id INTEGER PRIMARY KEY,
    order_item_id INTEGER,
    processed_at TEXT,
    quantity INTEGER,
    reason_id INTEGER,
    requested_at TEXT,
    status TEXT
);
INSERT INTO order_returns_new (id, order_item_id, processed_at, quantity, reason_id, requested_at, status)
SELECT id, order_item_id, processed_at, quantity, reason_id, requested_at, status FROM order_returns;
DROP TABLE order_returns;
ALTER TABLE order_returns_new RENAME TO order_returns;
```
After this, inserts that leave out `id` get the next number automatically (21 onwards).

## Planned tools (LangChain `@tool`, docstrings tell the LLM when to use them)
1. `check_order_status(order_id: int)` — joins orders, users, order_statuses, shipments (LEFT), order_items, products. Returns status, items (with item ids), shipping and delivery info.
2. `lookup_return_policy()` — static policy (30-day window, 5-7 day refund) plus reasons read from `return_reasons`.
3. `process_return_request(order_item_id: int, reason_id: int, quantity: int = 1)` — validates: item exists, order status is `delivered`, within 30 days of `shipments.delivered_at`, valid quantity and reason, no existing return; then INSERTs into `order_returns` with status `requested`.

## Build plan (go one step at a time, confirm each step works before the next)
1. Load the dataset CSVs into `ecommerce.db` (one-time `load_data.py` script), then test with `SELECT COUNT(*) FROM orders` → 360. Also check row counts of the other tables and that `delivered_at` looks like `YYYY-MM-DD HH:MM:SS`. **← current step**
2. Run the pending schema fix above.
3. Write the `run_query` helper and tool 1; test with real order IDs.
4. Add tools 2 and 3; test the return flow.
5. Swap the LLM to Groq (`ChatGroq`), then update the system prompt: generic e-commerce store, numeric order IDs, item/reason ids.
6. Replace `InMemorySaver` with `SqliteSaver` from `langgraph-checkpoint-sqlite`, using a separate file `checkpoints.db` and a connection with `check_same_thread=False`. Check the current LangGraph docs for exact usage.
7. Hardening: open lookups with a read-only connection (`sqlite3.connect("file:ecommerce.db?mode=ro", uri=True)`) and use a separate writable connection only for returns; customer verification (email) before showing order data; human-in-the-loop for refunds.

## Later phases (NOT now)
After Phase 1 works end to end, features will be added to take the project from intermediate to advanced. Do not build these until asked. Moving the database to PostgreSQL is one of the options for later.

## Coding rules
- Always use **parameterized queries** (`?` placeholders in SQLite); never build SQL with f-strings.
- Tools return short, plain-text strings the LLM can read; handle "not found" gracefully.
- Keep changes small and incremental; explain briefly what changed and why.
- Do not invent columns or tables; use only the schema above.
- Do not add features beyond the current step unless asked.
- Keep code as simple as possible and use current, supported library versions; flag deprecated patterns.
- Don't claim metrics or results that haven't been measured.

## Author's goal
This is a portfolio project for AI Engineer roles. The final repo needs a README with: Title, Project Summary, Problem, Dataset, Approach/Methodology, Model/Algorithm, Results, Key Visualizations, How to Run, Tech Stack, Project Structure, Next Steps, Author.
