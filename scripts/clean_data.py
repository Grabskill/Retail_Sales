"""Build star-schema tables from raw e-commerce CSVs.

Design choices (intentional, not silent fixes):
- Duplicate customer/order rows are dropped; conflicting versions were not present.
- Missing foreign keys are flagged, not imputed.
- Invalid dates are nulled and flagged, not guessed.
- Product category labels are standardized; mismatched category/sub-category
  pairs are flagged with a suggested category from majority vote.
- Negative quantity is treated as a return (`is_return`), not dropped.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT
OUT_DIR = ROOT / "cleaned_files"

CATEGORY_MAP = {
    "electronics": "Electronics",
    "office supplies": "Office Supplies",
    "furniture": "Furniture",
    "clothing": "Clothing",
    "home & kitchen": "Home & Kitchen",
}


def standardize_category(value: object) -> object:
    if pd.isna(value):
        return value
    cleaned = str(value).strip()
    return CATEGORY_MAP.get(cleaned.lower(), cleaned)


def clean_customers(raw: pd.DataFrame) -> pd.DataFrame:
    return (
        raw.drop_duplicates(subset=["customer_id"], keep="first")
        .sort_values("customer_id")
        .reset_index(drop=True)
    )


def clean_products(raw: pd.DataFrame) -> pd.DataFrame:
    products = raw.copy()
    products["category_original"] = products["category"]
    products["category"] = products["category_original"].map(standardize_category)
    majority = (
        products.groupby(["sub_category", "category"])
        .size()
        .reset_index(name="n")
        .sort_values(["sub_category", "n"], ascending=[True, False])
        .drop_duplicates("sub_category")
        .set_index("sub_category")["category"]
    )
    products["suggested_category"] = products["sub_category"].map(majority)
    products["category_subcategory_mismatch"] = (
        products["category"] != products["suggested_category"]
    )
    return products[
        [
            "product_id",
            "product_name",
            "category",
            "sub_category",
            "cost",
            "selling_price",
            "category_original",
            "suggested_category",
            "category_subcategory_mismatch",
        ]
    ].sort_values("product_id").reset_index(drop=True)


def clean_regions(raw: pd.DataFrame) -> pd.DataFrame:
    return (
        raw[["region_id", "state", "city", "region"]]
        .drop_duplicates(subset=["region_id"])
        .sort_values("region_id")
        .reset_index(drop=True)
    )


def clean_orders(raw: pd.DataFrame) -> pd.DataFrame:
    orders = raw.drop_duplicates(keep="first").copy()
    parsed = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["invalid_order_date"] = parsed.isna()
    orders["order_date"] = parsed.dt.strftime("%Y-%m-%d")
    orders.loc[parsed.isna(), "order_date"] = pd.NA
    orders["missing_customer_id"] = orders["customer_id"].isna()
    orders["missing_product_id"] = orders["product_id"].isna()
    orders["is_return"] = orders["quantity"] < 0
    return (
        orders[
            [
                "order_id",
                "order_date",
                "customer_id",
                "product_id",
                "region_id",
                "quantity",
                "discount",
                "sales_amount",
                "cost_amount",
                "profit",
                "is_return",
                "invalid_order_date",
                "missing_customer_id",
                "missing_product_id",
            ]
        ]
        .sort_values("order_id")
        .reset_index(drop=True)
    )


def build_dim_date(fact: pd.DataFrame) -> pd.DataFrame:
    valid = fact.loc[~fact["invalid_order_date"] & fact["order_date"].notna(), "order_date"]
    dates = pd.to_datetime(valid, errors="coerce").dropna().drop_duplicates().sort_values()
    dim = pd.DataFrame({"date": dates.dt.strftime("%Y-%m-%d")})
    dt = pd.to_datetime(dim["date"])
    dim["date_key"] = dt.dt.strftime("%Y%m%d").astype(int)
    dim["day"] = dt.dt.day
    dim["month"] = dt.dt.month
    dim["month_name"] = dt.dt.month_name()
    dim["quarter"] = dt.dt.quarter
    dim["year"] = dt.dt.year
    return dim[["date_key", "date", "day", "month", "month_name", "quarter", "year"]]


def run() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    customers = clean_customers(pd.read_csv(RAW_DIR / "customers_raw.csv"))
    products = clean_products(pd.read_csv(RAW_DIR / "products_raw.csv"))
    regions = clean_regions(pd.read_csv(RAW_DIR / "regions_raw.csv"))
    fact = clean_orders(pd.read_csv(RAW_DIR / "orders_raw.csv"))
    dim_date = build_dim_date(fact)

    customers.to_csv(OUT_DIR / "dim_customer.csv", index=False)
    products.to_csv(OUT_DIR / "dim_product.csv", index=False)
    regions.to_csv(OUT_DIR / "dim_region.csv", index=False)
    dim_date.to_csv(OUT_DIR / "dim_date.csv", index=False)
    fact.to_csv(OUT_DIR / "fact_sales.csv", index=False)

    print(f"Wrote star schema to {OUT_DIR}")
    print(f"  dim_customer {len(customers):>6} rows")
    print(f"  dim_product  {len(products):>6} rows")
    print(f"  dim_region   {len(regions):>6} rows")
    print(f"  dim_date     {len(dim_date):>6} rows")
    print(f"  fact_sales   {len(fact):>6} rows")


if __name__ == "__main__":
    run()
