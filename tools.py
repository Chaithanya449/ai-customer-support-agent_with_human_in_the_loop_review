"""SQLite-backed tools for the e-commerce support agent."""

from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any

from langchain_core.tools import tool


DB_PATH = Path(__file__).resolve().parent / "ecommerce.db"


def run_query(
    query: str,
    parameters: tuple[Any, ...] = (),
    *,
    fetch: bool = True,
) -> list[sqlite3.Row] | int:
    """Run a parameterized SQL query against the project database."""
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            cursor = connection.execute(query, parameters)
            if fetch:
                return cursor.fetchall()
            return cursor.rowcount


@tool
def check_order_status(order_id: int) -> str:
    """Look up an order by numeric ID and report its status, items, and shipment details."""
    rows = run_query(
        """
        SELECT o.id AS order_id, u.first_name, u.last_name,
               os.status_name AS order_status, s.tracking_number,
               s.shipped_at, s.delivered_at, oi.id AS order_item_id,
               p.name AS product_name, oi.quantity, oi.unit_price
        FROM orders AS o
        JOIN users AS u ON u.id = o.user_id
        JOIN order_statuses AS os ON os.id = o.order_status_id
        LEFT JOIN shipments AS s ON s.order_id = o.id
        LEFT JOIN order_items AS oi ON oi.order_id = o.id
        LEFT JOIN products AS p ON p.id = oi.product_id
        WHERE o.id = ?
        ORDER BY oi.id
        """,
        (order_id,),
    )
    if not rows:
        return f"No order found with ID {order_id}."

    first = rows[0]
    lines = [
        f"Order {first['order_id']} for {first['first_name']} {first['last_name']}",
        f"Status: {first['order_status']}",
    ]
    items = [row for row in rows if row["order_item_id"] is not None]
    if items:
        lines.append("Items:")
        for item in items:
            lines.append(
                f"- Item ID {item['order_item_id']}: {item['product_name']} "
                f"(quantity {item['quantity']}, unit price ${item['unit_price']:.2f})"
            )
    else:
        lines.append("Items: none listed")

    if first["tracking_number"]:
        lines.append(f"Tracking number: {first['tracking_number']}")
    else:
        lines.append("Tracking: not available")
    if first["shipped_at"]:
        lines.append(f"Shipped at: {first['shipped_at']}")
    if first["delivered_at"]:
        lines.append(f"Delivered at: {first['delivered_at']}")
    return "\n".join(lines)


@tool
def lookup_return_policy() -> str:
    """Explain the 7-day return window and refund timing; list valid return reason IDs."""
    rows = run_query("SELECT id, reason_text FROM return_reasons ORDER BY id")
    reasons = "\n".join(f"{row['id']}: {row['reason_text']}" for row in rows)
    return (
        "Returns can be requested within 7 days of delivery. Approved refunds are "
        "typically processed in 5-7 days. Valid reasons:\n" + reasons
    )


@tool
def process_return_request(order_item_id: int, reason_id: int, quantity: int = 1) -> str:
    """Request a return for a delivered item within 7 days of delivery."""
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            item = connection.execute(
                """
                SELECT oi.quantity, os.status_name, s.delivered_at,
                       EXISTS(SELECT 1 FROM return_reasons WHERE id = ?) AS valid_reason,
                       EXISTS(SELECT 1 FROM order_returns WHERE order_item_id = oi.id) AS has_return
                FROM order_items AS oi
                JOIN orders AS o ON o.id = oi.order_id
                JOIN order_statuses AS os ON os.id = o.order_status_id
                LEFT JOIN shipments AS s ON s.order_id = o.id
                WHERE oi.id = ?
                """,
                (reason_id, order_item_id),
            ).fetchone()
            if item is None:
                return f"No order item found with ID {order_item_id}."
            if item["status_name"] != "delivered" or not item["delivered_at"]:
                return "The order item must be delivered before it can be returned."
            if quantity < 1 or quantity > item["quantity"]:
                return f"Enter a return quantity from 1 to {item['quantity']}."
            if not item["valid_reason"]:
                return "Invalid return reason. Check the return policy for valid reason IDs."
            if item["has_return"]:
                return f"A return request already exists for order item {order_item_id}."

            eligible = connection.execute(
                "SELECT julianday('now') - julianday(?) <= 7",
                (item["delivered_at"],),
            ).fetchone()[0]
            if not eligible:
                return "This item is outside the 7-day return window."

            cursor = connection.execute(
                """INSERT INTO order_returns
                   (order_item_id, processed_at, quantity, reason_id, requested_at, status)
                   VALUES (?, NULL, ?, ?, datetime('now'), 'requested')""",
                (order_item_id, quantity, reason_id),
            )
            return f"Return request {cursor.lastrowid} created; status: requested."


def ensure_review_schema() -> None:
    """Create tables used to record human return decisions and issued refunds."""
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS return_refunds (
                return_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL,
                amount REAL NOT NULL, refunded_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS return_review_notes (
                return_id INTEGER PRIMARY KEY, reviewer_note TEXT, reviewed_at TEXT
            )"""
        )


def ensure_refund_requests_table() -> None:
    """Create the table for order-level refund requests awaiting human review."""
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS refund_requests (
                id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL UNIQUE,
                amount REAL NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('requested', 'approved', 'rejected')),
                requested_at TEXT NOT NULL, reviewed_at TEXT, reviewer_note TEXT
            )"""
        )


@tool
def request_refund(order_id: int) -> str:
    """Submit an eligible order refund for human review; this does not issue a refund."""
    ensure_refund_requests_table()
    orders = run_query(
        """SELECT o.id, o.total, os.status_name,
                  EXISTS(SELECT 1 FROM payments p WHERE p.order_id=o.id AND p.status='completed') AS paid,
                  EXISTS(SELECT 1 FROM payments p WHERE p.order_id=o.id AND p.status='refunded') AS refunded
           FROM orders o JOIN order_statuses os ON os.id=o.order_status_id WHERE o.id=?""",
        (order_id,),
    )
    if not orders:
        return f"No order found with ID {order_id}."
    order = orders[0]
    if not order["paid"]:
        return "This order has no completed payment eligible for a refund request."
    if order["refunded"] or order["status_name"] == "refunded":
        return "This order has already been refunded."
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            existing = connection.execute(
                "SELECT id, status FROM refund_requests WHERE order_id=?", (order_id,)
            ).fetchone()
            if existing:
                return f"Refund request {existing['id']} is already {existing['status']} for order {order_id}."
            cursor = connection.execute(
                "INSERT INTO refund_requests (order_id, amount, status, requested_at) VALUES (?, ?, 'requested', datetime('now'))",
                (order_id, order["total"]),
            )
            request_id = cursor.lastrowid
    return f"Refund request {request_id} for order {order_id} (${order['total']:.2f}) was submitted for human review; status: requested."


@tool
def check_refund_status(order_id: int) -> str:
    """Check human-review decisions and refund records for an order."""
    ensure_refund_requests_table()
    ensure_review_schema()
    order_requests = run_query(
        "SELECT id, amount, status FROM refund_requests WHERE order_id=?", (order_id,)
    )
    return_requests = run_query(
        """SELECT r.id, r.status, rr.amount, rrn.reviewer_note
           FROM order_returns r JOIN order_items oi ON oi.id=r.order_item_id
           LEFT JOIN return_refunds rr ON rr.return_id=r.id
           LEFT JOIN return_review_notes rrn ON rrn.return_id=r.id
           WHERE oi.order_id=? ORDER BY r.id""",
        (order_id,),
    )
    lines = [f"Order refund request {r['id']}: {r['status']} (${r['amount']:.2f})." for r in order_requests]
    for row in return_requests:
        line = f"Return request {row['id']}: {row['status']}"
        line += f"; ${row['amount']:.2f} refunded." if row["amount"] is not None else "; no refund recorded."
        if row["reviewer_note"]:
            line += f" Reviewer note: {row['reviewer_note']}"
        lines.append(line)
    return "\n".join(lines) if lines else f"No refund or return requests found for order {order_id}."


def list_pending_reviews() -> list[sqlite3.Row]:
    """List pending return requests with order and customer context for reviewers."""
    ensure_review_schema()
    return run_query(
        """SELECT r.id AS request_id, r.order_item_id, r.quantity, r.reason_id, r.requested_at,
                  oi.order_id, oi.unit_price, p.name AS product_name, rr.reason_text,
                  u.first_name, u.last_name, u.email, os.status_name AS order_status
           FROM order_returns r JOIN order_items oi ON oi.id=r.order_item_id
           JOIN products p ON p.id=oi.product_id JOIN orders o ON o.id=oi.order_id
           JOIN users u ON u.id=o.user_id JOIN order_statuses os ON os.id=o.order_status_id
           JOIN return_reasons rr ON rr.id=r.reason_id
           WHERE r.status='requested' ORDER BY r.requested_at, r.id"""
    )


def list_pending_refunds() -> list[sqlite3.Row]:
    """List pending order-level refund requests for human review."""
    ensure_refund_requests_table()
    return run_query(
        """SELECT rr.id AS request_id, rr.order_id, rr.amount, rr.requested_at,
                  u.first_name, u.last_name, u.email, os.status_name AS order_status
           FROM refund_requests rr JOIN orders o ON o.id=rr.order_id
           JOIN users u ON u.id=o.user_id JOIN order_statuses os ON os.id=o.order_status_id
           WHERE rr.status='requested' ORDER BY rr.requested_at, rr.id"""
    )


def review_return(request_id: int, decision: str, note: str = "") -> str:
    """Record a human return decision and issue an eligible item refund on approval."""
    ensure_review_schema()
    decision = decision.lower()
    if decision not in {"approve", "reject"}:
        return "Decision must be approve or reject."
    status = "approved" if decision == "approve" else "rejected"
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            request = connection.execute(
                """SELECT r.*, oi.order_id, oi.unit_price FROM order_returns r
                   JOIN order_items oi ON oi.id=r.order_item_id WHERE r.id=?""",
                (request_id,),
            ).fetchone()
            if request is None:
                return f"No return request found with ID {request_id}."
            if request["status"] != "requested":
                return f"Return request {request_id} has already been {request['status']}."
            refund_amount = 0.0
            if decision == "approve":
                payment = connection.execute(
                    "SELECT id, amount FROM payments WHERE order_id=? AND status='completed' ORDER BY id LIMIT 1",
                    (request["order_id"],),
                ).fetchone()
                if payment is None:
                    return "No completed payment remains; request stays pending and no refund was issued."
                already_refunded = connection.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM return_refunds WHERE order_id=?",
                    (request["order_id"],),
                ).fetchone()[0]
                refund_amount = min(request["unit_price"] * request["quantity"], max(0.0, payment["amount"] - already_refunded))
                if refund_amount <= 0:
                    return "No refundable paid amount remains; request stays pending."
                connection.execute(
                    "INSERT INTO return_refunds (return_id, order_id, amount, refunded_at) VALUES (?, ?, ?, ?)",
                    (request_id, request["order_id"], refund_amount, now),
                )
                if already_refunded + refund_amount >= payment["amount"]:
                    connection.execute("UPDATE payments SET status='refunded' WHERE id=?", (payment["id"],))
            connection.execute("UPDATE order_returns SET status=?, processed_at=? WHERE id=?", (status, now, request_id))
            connection.execute(
                "INSERT OR REPLACE INTO return_review_notes (return_id, reviewer_note, reviewed_at) VALUES (?, ?, ?)",
                (request_id, note, now),
            )
    if decision == "approve":
        return f"Return request {request_id} approved by human review; ${refund_amount:.2f} refunded for order {request['order_id']}."
    return f"Return request {request_id} rejected by human review for order {request['order_id']}."


def review_refund(request_id: int, decision: str, note: str = "") -> str:
    """Record a human refund decision; only approval changes payment and order status."""
    ensure_refund_requests_table()
    decision = decision.lower()
    if decision not in {"approve", "reject"}:
        return "Decision must be approve or reject."
    status = "approved" if decision == "approve" else "rejected"
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            request = connection.execute("SELECT * FROM refund_requests WHERE id=?", (request_id,)).fetchone()
            if request is None:
                return f"No refund request found with ID {request_id}."
            if request["status"] != "requested":
                return f"Refund request {request_id} has already been {request['status']}."
            if decision == "approve":
                payment = connection.execute(
                    "SELECT 1 FROM payments WHERE order_id=? AND status='completed' LIMIT 1", (request["order_id"],)
                ).fetchone()
                if payment is None:
                    return "No completed payment remains to refund; request remains pending."
                connection.execute("UPDATE payments SET status='refunded' WHERE order_id=? AND status='completed'", (request["order_id"],))
                connection.execute(
                    "UPDATE orders SET order_status_id=(SELECT id FROM order_statuses WHERE status_name='refunded') WHERE id=?",
                    (request["order_id"],),
                )
            connection.execute(
                "UPDATE refund_requests SET status=?, reviewed_at=?, reviewer_note=? WHERE id=?",
                (status, now, note, request_id),
            )
    return f"Refund request {request_id} {status} by human review for order {request['order_id']}."


tools = [check_order_status, lookup_return_policy, process_return_request, request_refund, check_refund_status]
