"""Profile raw CSVs before modeling.

Prints row counts, dtypes, missingness, duplicate keys, and categorical drift.
Run this before `clean_data.py` when presenting the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "orders": ROOT / "orders_raw.csv",
    "customers": ROOT / "customers_raw.csv",
    "products": ROOT / "products_raw.csv",
    "regions": ROOT / "regions_raw.csv",
}


def profile(name: str, path: Path) -> None:
    df = pd.read_csv(path)
    print(f"\n=== {name} ({path.name}) ===")
    print(f"rows={len(df):,}  cols={df.shape[1]}")
    print(df.dtypes.to_string())
    print("missing:")
    print(df.isna().sum().to_string())
    print(f"full-row duplicates: {int(df.duplicated().sum())}")


def main() -> None:
    orders = pd.read_csv(FILES["orders"])
    customers = pd.read_csv(FILES["customers"])
    products = pd.read_csv(FILES["products"])
    regions = pd.read_csv(FILES["regions"])

    for name, path in FILES.items():
        profile(name, path)

    print("\n=== referential integrity ===")
    print(
        "orphan customer_id",
        int(orders["customer_id"].notna().sum() - orders["customer_id"].dropna().isin(customers["customer_id"]).sum()),
    )
    print(
        "orphan product_id",
        int(orders["product_id"].notna().sum() - orders["product_id"].dropna().isin(products["product_id"]).sum()),
    )
    print("orphan region_id", int((~orders["region_id"].isin(regions["region_id"])).sum()))
    print("product category labels:", sorted(products["category"].astype(str).unique().tolist()))
    parsed = pd.to_datetime(orders["order_date"], errors="coerce")
    print("unparseable order_date", int(parsed.isna().sum()))
    print("negative quantity", int((orders["quantity"] < 0).sum()))


if __name__ == "__main__":
    main()
