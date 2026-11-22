"""Try a customer return flow with: python test.py [order_id]"""

import argparse
from contextlib import closing
import sqlite3

import tools


parser = argparse.ArgumentParser()
parser.add_argument("order_id", nargs="?", type=int, default=1)
args = parser.parse_args()

# Example customer choices for this quick run. Change these when trying a
# different item or reason from the order and return policy output.
reason_id = 1
return_quantity = 1

print("CHECK ORDER STATUS")
print(tools.check_order_status.invoke({"order_id": args.order_id}))

with closing(sqlite3.connect(tools.DB_PATH)) as db, db:
    item = db.execute(
        "SELECT id FROM order_items WHERE order_id = ? ORDER BY id LIMIT 1",
        (args.order_id,),
    ).fetchone()

if item is None:
    print(f"Cannot request a return: order {args.order_id} has no items.")
else:
    order_item_id = item[0]
    print("\nRETURN POLICY")
    print(tools.lookup_return_policy.invoke({}))
    print(
        f"\nCustomer requests return: item ID {order_item_id}, "
        f"reason ID {reason_id}, quantity {return_quantity}"
    )

    result = tools.process_return_request.invoke(
        {
            "order_item_id": order_item_id,
            "reason_id": reason_id,
            "quantity": return_quantity,
        }
    )
    accepted = result.startswith("Return request ")
    print(f"Return {'accepted' if accepted else 'declined'}: {result}")
