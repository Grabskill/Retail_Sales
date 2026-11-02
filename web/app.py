from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "cleaned_files"


@st.cache_data
def load_data():
    fact = pd.read_csv(CLEAN / "fact_sales.csv")
    products = pd.read_csv(CLEAN / "dim_product.csv")
    regions = pd.read_csv(CLEAN / "dim_region.csv")

    df = fact.loc[~fact["invalid_order_date"]].copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["year"] = df["order_date"].dt.year.astype(int)
    df["month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()

    df = df.merge(regions[["region_id", "region", "state"]], on="region_id", how="left")
    df = df.merge(
        products[["product_id", "product_name", "category", "sub_category"]],
        on="product_id",
        how="left",
    )
    df = df.loc[df["category"].notna() & df["region"].notna()]
    return df


def inr(n: float) -> str:
    return f"{n:,.0f}"


st.set_page_config(page_title="E-commerce Sales Dashboard", layout="wide")
st.title("E-commerce sales dashboard")
st.caption(
    "Streamlit view of the cleaned star schema · Jan 2024–Dec 2025 · net of returns · "
    "invalid dates and missing product IDs excluded"
)

df = load_data()

years = ["All years"] + [str(y) for y in sorted(df["year"].unique())]
regions = ["All regions"] + sorted(df["region"].dropna().unique().tolist())
categories = ["All categories"] + sorted(df["category"].dropna().unique().tolist())

c1, c2, c3 = st.columns(3)
year_sel = c1.selectbox("Year", years)
region_sel = c2.selectbox("Region", regions)
category_sel = c3.selectbox("Category", categories)

view = df
if year_sel != "All years":
    view = view.loc[view["year"] == int(year_sel)]
if region_sel != "All regions":
    view = view.loc[view["region"] == region_sel]
if category_sel != "All categories":
    view = view.loc[view["category"] == category_sel]

revenue = float(view["sales_amount"].sum())
profit = float(view["profit"].sum())
orders = int(view["order_id"].nunique())
customers = int(view["customer_id"].nunique(dropna=True))
margin = (profit / revenue * 100) if revenue else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Revenue", inr(revenue), help=f"{orders:,} orders in view")
k2.metric("Profit", inr(profit), help=f"Margin {margin:.1f}%")
k3.metric("Orders", f"{orders:,}")
k4.metric("Customers", f"{customers:,}")

monthly = (
    view.groupby("month", as_index=False)
    .agg(Revenue=("sales_amount", "sum"), Profit=("profit", "sum"))
    .sort_values("month")
)
fig_month = px.line(
    monthly.melt(id_vars="month", value_vars=["Revenue", "Profit"], var_name="Metric", value_name="Amount"),
    x="month",
    y="Amount",
    color="Metric",
    markers=True,
    title="Monthly sales trend",
)
fig_month.update_layout(legend_title_text="", hovermode="x unified")
st.plotly_chart(fig_month, use_container_width=True)

left, right = st.columns(2)

by_cat = (
    view.groupby("category", as_index=False)["sales_amount"]
    .sum()
    .rename(columns={"sales_amount": "Revenue", "category": "Category"})
    .sort_values("Revenue", ascending=False)
)
fig_cat = px.bar(by_cat, x="Category", y="Revenue", title="Revenue by category")
fig_cat.update_layout(showlegend=False)
left.plotly_chart(fig_cat, use_container_width=True)

by_region = (
    view.groupby("region", as_index=False)["profit"]
    .sum()
    .rename(columns={"profit": "Profit", "region": "Region"})
    .sort_values("Profit", ascending=True)
)
fig_region = px.bar(by_region, x="Profit", y="Region", orientation="h", title="Profit by region")
fig_region.update_layout(showlegend=False)
right.plotly_chart(fig_region, use_container_width=True)

st.subheader("Top 10 products by revenue")
if view.empty:
    st.info("No products in this filter.")
else:
    top = (
        view.groupby(["product_id", "product_name"], as_index=False)
        .agg(Revenue=("sales_amount", "sum"), Profit=("profit", "sum"))
        .sort_values("Revenue", ascending=False)
        .head(10)
    )
    top["Margin %"] = (top["Profit"] / top["Revenue"] * 100).round(1)
    top["Product"] = top["product_id"] + " · " + top["product_name"]
    display = pd.DataFrame(
        {
            "Product": top["Product"],
            "Revenue": top["Revenue"].round(0).astype("int64").map(lambda n: f"{n:,}"),
            "Profit": top["Profit"].round(0).astype("int64").map(lambda n: f"{n:,}"),
            "Margin %": top["Margin %"].map(lambda n: f"{n:.1f}"),
        }
    )
    st.dataframe(display, hide_index=True, use_container_width=True)
