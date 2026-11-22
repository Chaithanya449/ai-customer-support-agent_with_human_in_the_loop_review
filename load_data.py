"""Load the project's CSV dataset into a local SQLite database."""

from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
CSV_DIR = PROJECT_DIR / "ecommerce-csv"
DB_PATH = PROJECT_DIR / "ecommerce.db"


def main() -> None:
    csv_files = sorted(CSV_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {CSV_DIR}")

    with sqlite3.connect(DB_PATH) as connection:
        for csv_path in csv_files:
            table_name = csv_path.stem
            dataframe = pd.read_csv(csv_path)
            dataframe.to_sql(table_name, connection, if_exists="replace", index=False)
            print(f"Loaded {table_name}: {len(dataframe)} rows")

        # Confirm the expected order count and inspect the delivery timestamp format.
        order_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        if order_count != 377:
            raise ValueError(f"Expected 377 orders, found {order_count}")

        shipment_count = connection.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        timestamp_samples = connection.execute(
            "SELECT delivered_at FROM shipments "
            "WHERE delivered_at IS NOT NULL LIMIT 5"
        ).fetchall()

    print(f"Verified orders: {order_count}")
    print(f"Verified shipments: {shipment_count}")
    print("Sample delivered_at values:")
    for (delivered_at,) in timestamp_samples:
        print(f"  {delivered_at}")


if __name__ == "__main__":
    main()
