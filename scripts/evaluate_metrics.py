"""Evaluate commercial and quality metrics from the cleaned star schema.

Writes a compact CSV to reports/ so dashboard numbers can be audited independently
of Streamlit.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "cleaned_files"
REPORTS = ROOT / "reports"


def load() -> pd.DataFrame:
    fact = pd.read_csv(CLEAN / "fact_sales.csv")
    products = pd.read_csv(CLEAN / "dim_product.csv")
    regions = pd.read_csv(CLEAN / "dim_region.csv")
    df = fact.loc[~fact["invalid_order_date"]].merge(
        regions[["region_id", "region", "state"]], on="region_id", how="left"
    )
    df = df.merge(
        products[["product_id", "product_name", "category", "sub_category"]],
        on="product_id",
        how="left",
    )
    return df.loc[df["category"].notna()]


def main() -> None:
    df = load()
    REPORTS.mkdir(exist_ok=True)

    revenue = float(df["sales_amount"].sum())
    profit = float(df["profit"].sum())
    kpis = pd.DataFrame(
        [
            {"metric": "revenue", "value": round(revenue, 2)},
            {"metric": "profit", "value": round(profit, 2)},
            {"metric": "margin_pct", "value": round(profit / revenue * 100, 2)},
            {"metric": "orders", "value": int(df["order_id"].nunique())},
            {"metric": "customers", "value": int(df["customer_id"].nunique(dropna=True))},
            {"metric": "return_orders", "value": int(df["is_return"].sum())},
        ]
    )

    top = (
        df.groupby(["product_id", "product_name", "category"], as_index=False)
        .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"))
        .assign(margin_pct=lambda x: x["profit"] / x["revenue"] * 100)
        .sort_values("revenue", ascending=False)
        .head(10)
    )
    regions = (
        df.groupby("region", as_index=False)
        .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"))
        .sort_values("profit", ascending=False)
    )
    prod = (
        df.groupby(["product_id", "product_name", "category"], as_index=False)
        .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"))
    )
    prod["margin_pct"] = prod["profit"] / prod["revenue"] * 100
    high_low = prod.loc[
        (prod["revenue"] >= prod["revenue"].quantile(0.75))
        & (prod["margin_pct"] <= prod["margin_pct"].quantile(0.25))
    ].sort_values("revenue", ascending=False)

    kpis.to_csv(REPORTS / "kpis.csv", index=False)
    top.to_csv(REPORTS / "top_products.csv", index=False)
    regions.to_csv(REPORTS / "profit_by_region.csv", index=False)
    high_low.to_csv(REPORTS / "high_revenue_low_margin.csv", index=False)

    print("KPIs")
    print(kpis.to_string(index=False))
    print("\nTop 3 products by revenue")
    print(top.head(3).to_string(index=False))
    print("\nProfit by region")
    print(regions.to_string(index=False))
    print("\nHigh revenue, low margin")
    print(high_low.to_string(index=False) if len(high_low) else "none")
    print(f"\nWrote CSVs to {REPORTS}")


if __name__ == "__main__":
    main()
