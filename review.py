"""Local console for a human to review pending return requests."""

from tools import (
    ensure_refund_requests_table,
    ensure_review_schema,
    list_pending_refunds,
    list_pending_reviews,
    review_refund,
    review_return,
)


def main() -> None:
    ensure_review_schema()
    ensure_refund_requests_table()
    print("Human review console. You are acting as the reviewer.")
    while True:
        returns = list_pending_reviews()
        refunds = list_pending_refunds()
        if not returns and not refunds:
            print("No return or refund requests are pending review.")
            return
        print("\nPending return requests (use R + ID):")
        for request in returns:
            print(
                f"R{request['request_id']} | Order {request['order_id']} | "
                f"Item {request['order_item_id']}: {request['product_name']} | "
                f"quantity {request['quantity']} | reason: {request['reason_text']} | "
                f"unit price ${request['unit_price']:.2f} | {request['first_name']} "
                f"{request['last_name']} <{request['email']}> | order status: "
                f"{request['order_status']} | submitted: {request['requested_at']}"
            )
        print("\nPending order refund requests (use F + ID):")
        for request in refunds:
            print(
                f"F{request['request_id']} | Order {request['order_id']} | "
                f"${request['amount']:.2f} | {request['first_name']} {request['last_name']} "
                f"<{request['email']}> | order status: {request['order_status']} | "
                f"submitted: {request['requested_at']}"
            )
        choice = input("Request to review (R<ID>/F<ID>), or 'q' to quit: ").strip().upper()
        if choice.lower() in {"q", "quit", "exit"}:
            return
        if len(choice) < 2 or choice[0] not in {"R", "F"} or not choice[1:].isdigit():
            print("Choose a queued request using R<ID> or F<ID>.")
            continue
        request_id = int(choice[1:])
        is_return = choice[0] == "R"
        queue = returns if is_return else refunds
        if not any(row["request_id"] == request_id for row in queue):
            print("That request is not in the pending queue.")
            continue
        decision = input("Decision (approve/reject): ").strip().lower()
        if decision not in {"approve", "reject"}:
            print("Decision must be approve or reject; request remains pending.")
            continue
        note = input("Reviewer note (optional): ").strip()
        if is_return:
            print(review_return(request_id, decision, note))
        else:
            print(review_refund(request_id, decision, note))


if __name__ == "__main__":
    main()
