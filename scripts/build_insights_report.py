"""Build a presentation-ready Word insights pack with embedded charts."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "cleaned_files"
DOCS = ROOT / "docs"
CHARTS = DOCS / "charts"
OUT = DOCS / "Business_Insights_Report.docx"
OUT_MD = DOCS / "Business_Insights_Report.md"

NAVY = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x5B, 0x67, 0x75)
NAVY_HEX = "#1F4E79"
TEAL_HEX = "#2E7D6F"
AMBER_HEX = "#B45309"
GRID = "#E4E8EE"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.edgecolor": GRID,
        "axes.labelcolor": "#1C2430",
        "xtick.color": "#5B6775",
        "ytick.color": "#5B6775",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def money(n: float) -> str:
    return f"{n:,.0f}"


def pct(n: float) -> str:
    return f"{n:.1f}%"


def shade(cell, fill: str) -> None:
    tc = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")
    tc.append(shd)


def set_cell_text(cell, text: str, bold: bool = False, align: str = "left", color: RGBColor | None = None, size: int = 10) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = {
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
    }.get(align, WD_ALIGN_PARAGRAPH.LEFT)
    run = p.add_run(str(text))
    run.font.size = Pt(size)
    run.font.name = "Calibri"
    run.bold = bold
    if color:
        run.font.color.rgb = color


def add_table(doc: Document, headers: list[str], rows: list[list[str]], right_cols: set[int] | None = None) -> None:
    right_cols = right_cols or set()
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        set_cell_text(hdr.cells[i], h, bold=True, align="center", color=RGBColor(255, 255, 255))
        shade(hdr.cells[i], "1F4E79")
    for r_i, row in enumerate(rows, start=1):
        for c_i, val in enumerate(row):
            set_cell_text(table.rows[r_i].cells[c_i], val, align="right" if c_i in right_cols else "left")
            if r_i % 2 == 0:
                shade(table.rows[r_i].cells[c_i], "F4F6F8")
    doc.add_paragraph()


def save_chart(fig, name: str) -> Path:
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / name
    fig.savefig(path, format="png", dpi=160, bbox_inches="tight")
    return path


def add_chart(doc: Document, fig, filename: str, width: float = 6.5) -> Path:
    path = save_chart(fig, filename)
    plt.close(fig)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    return path


def caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED
    run.font.name = "Calibri"


def heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = NAVY


def body(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(8)
    for run in p.runs:
        run.font.size = Pt(11)
        run.font.name = "Calibri"


def bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text, style="List Bullet")
    for run in p.runs:
        run.font.size = Pt(11)
        run.font.name = "Calibri"


def page_break(doc: Document) -> None:
    doc.add_page_break()


def add_footer(section) -> None:
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Internal insights pack  ·  Jan 2024 – Dec 2025  ·  Page ")
    run.font.size = Pt(8)
    run.font.color.rgb = MUTED
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run2 = p.add_run()
    run2._r.append(fld_begin)
    run2._r.append(instr)
    run2._r.append(fld_end)
    run2.font.size = Pt(8)
    run2.font.color.rgb = MUTED


def load() -> pd.DataFrame:
    fact = pd.read_csv(CLEAN / "fact_sales.csv")
    products = pd.read_csv(CLEAN / "dim_product.csv")
    regions = pd.read_csv(CLEAN / "dim_region.csv")
    df = fact.loc[~fact["invalid_order_date"]].merge(
        regions[["region_id", "region", "state"]], on="region_id", how="left"
    )
    df = df.merge(
        products[["product_id", "product_name", "category"]],
        on="product_id",
        how="left",
    )
    df = df.loc[df["category"].notna()].copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["month"] = df["order_date"].dt.to_period("M").astype(str)
    return df


def fig_top10(top: pd.DataFrame):
    plot = top.sort_values("revenue", ascending=True)
    labels = plot["product_id"] + "  " + plot["product_name"].str.replace(" Product ", " ")
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.barh(labels, plot["revenue"] / 1e5, color=NAVY_HEX)
    ax.set_xlabel("Revenue (lakh)")
    ax.set_title("Top 10 products by revenue")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def fig_regions(regions: pd.DataFrame):
    plot = regions.sort_values("profit", ascending=True)
    fig, ax = plt.subplots(figsize=(8.2, 3.4))
    ax.barh(plot["region"], plot["profit"] / 1e5, color=TEAL_HEX)
    ax.set_xlabel("Profit (lakh)")
    ax.set_title("Profit by region")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def fig_monthly(monthly: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    x = range(len(monthly))
    ax.plot(list(x), monthly["revenue"] / 1e5, color=NAVY_HEX, linewidth=2.2, marker="o", markersize=3.5, label="Revenue")
    ax.plot(list(x), monthly["profit"] / 1e5, color=TEAL_HEX, linewidth=2.2, marker="o", markersize=3.5, label="Profit")
    ax.set_xticks(list(x))
    ax.set_xticklabels(monthly["month"].str[2:], rotation=45, ha="right")
    ax.set_ylabel("Amount (lakh)")
    ax.set_title("Monthly revenue and profit")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    fig.tight_layout()
    return fig


def fig_margin(high_low: pd.DataFrame, company_margin: float):
    plot = high_low.sort_values("margin", ascending=True)
    labels = plot["product_id"] + "  " + plot["product_name"].str.replace(" Product ", " ")
    fig, ax = plt.subplots(figsize=(8.2, 3.0))
    ax.barh(labels, plot["margin"], color=AMBER_HEX)
    ax.axvline(company_margin, color=NAVY_HEX, linestyle="--", linewidth=1.4, label=f"Company margin {company_margin:.1f}%")
    ax.set_xlabel("Profit margin (%)")
    ax.set_title("High-sales products with thin margin")
    ax.legend(frameon=False, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def kpi_strip(doc: Document, revenue, profit, margin, orders, customers) -> None:
    table = doc.add_table(rows=2, cols=4)
    table.style = "Table Grid"
    labels = ["Revenue", "Profit", "Margin", "Orders  /  customers"]
    values = [money(revenue), money(profit), pct(margin), f"{orders:,}  /  {customers:,}"]
    for i, (lab, val) in enumerate(zip(labels, values)):
        shade(table.rows[0].cells[i], "1F4E79")
        set_cell_text(table.rows[0].cells[i], lab, bold=True, align="center", color=RGBColor(255, 255, 255), size=9)
        shade(table.rows[1].cells[i], "F4F6F8")
        set_cell_text(table.rows[1].cells[i], val, bold=True, align="center", color=NAVY, size=14)
    doc.add_paragraph()


def build() -> Path:
    df = load()
    revenue = float(df["sales_amount"].sum())
    profit = float(df["profit"].sum())
    margin = profit / revenue * 100
    orders = int(df["order_id"].nunique())
    customers = int(df["customer_id"].nunique(dropna=True))

    top = (
        df.groupby(["product_id", "product_name", "category"], as_index=False)
        .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"))
        .assign(margin=lambda x: x["profit"] / x["revenue"] * 100)
        .sort_values("revenue", ascending=False)
        .head(10)
    )
    regions = (
        df.groupby("region", as_index=False)
        .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"), orders=("order_id", "nunique"))
        .assign(margin=lambda x: x["profit"] / x["revenue"] * 100)
        .sort_values("profit", ascending=False)
    )
    monthly = (
        df.groupby("month", as_index=False)
        .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"))
        .assign(margin=lambda x: x["profit"] / x["revenue"] * 100)
        .sort_values("month")
    )
    prod = (
        df.groupby(["product_id", "product_name", "category"], as_index=False)
        .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"))
    )
    prod["margin"] = prod["profit"] / prod["revenue"] * 100
    high_low = prod.loc[
        (prod["revenue"] >= prod["revenue"].quantile(0.75))
        & (prod["margin"] <= prod["margin"].quantile(0.25))
    ].sort_values("revenue", ascending=False)

    best_rev = monthly.loc[monthly["revenue"].idxmax()]
    worst_rev = monthly.loc[monthly["revenue"].idxmin()]
    best_p = monthly.loc[monthly["profit"].idxmax()]

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)
    add_footer(section)

    kicker = doc.add_paragraph()
    k = kicker.add_run("E-COMMERCE  ·  LEADERSHIP PACK")
    k.font.size = Pt(11)
    k.font.bold = True
    k.font.color.rgb = NAVY
    k.font.name = "Calibri"

    title = doc.add_paragraph()
    run = title.add_run("Business Insights Report")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = NAVY
    run.font.name = "Calibri"

    sub = doc.add_paragraph()
    r = sub.add_run("Sales, profit, and product mix  |  January 2024 – December 2025")
    r.font.size = Pt(13)
    r.font.color.rgb = MUTED

    body(
        doc,
        "This pack is for a leadership review. Charts and tables use the cleaned sales model. "
        "Returns stay in as negative sales. Orders with a broken date or no product are left out.",
    )

    heading(doc, "1. Snapshot", 1)
    kpi_strip(doc, revenue, profit, margin, orders, customers)
    bullet(doc, f"Two-year sales {money(revenue)} and profit {money(profit)} — about {pct(margin)} of each rupee of sales is profit.")
    bullet(doc, "The company is steady, not seasonal. The problem is mix: a few high-volume products keep little profit.")
    bullet(doc, "Regions look different in size, but they keep almost the same profit on each sale.")

    page_break(doc)
    heading(doc, "2. Top 10 products by revenue", 1)
    body(
        doc,
        "These ten products bring in about one-fifth of product sales. Kids Product 98 leads on both "
        "sales and margin. Paper Product 94 is the weak name in this list: it ranks tenth but keeps "
        "much less profit than the rest.",
    )
    add_chart(doc, fig_top10(top), "top10_revenue.png")
    caption(doc, "Figure 1. Revenue of the ten best-selling products (lakh).")
    add_table(
        doc,
        ["Rank", "Product", "Category", "Revenue", "Profit", "Margin"],
        [
            [
                str(i),
                f"{r.product_id}  {r.product_name}",
                r.category,
                money(r.revenue),
                money(r.profit),
                pct(r.margin),
            ]
            for i, r in enumerate(top.itertuples(index=False), start=1)
        ],
        right_cols={0, 3, 4, 5},
    )

    page_break(doc)
    heading(doc, "3. Which regions make the most profit?", 1)
    body(
        doc,
        "North makes the most profit, then East and South. West is a little behind because it has "
        "four states, not five. Central is only Madhya Pradesh, so its total is smaller. Margin is "
        "about 22–23% everywhere. North is not better at profit. It simply sells more.",
    )
    add_chart(doc, fig_regions(regions), "profit_by_region.png")
    caption(doc, "Figure 2. Total profit by region. Size follows coverage, not a better margin.")
    add_table(
        doc,
        ["Region", "Orders", "Revenue", "Profit", "Margin"],
        [
            [r.region, f"{int(r.orders):,}", money(r.revenue), money(r.profit), pct(r.margin)]
            for r in regions.itertuples(index=False)
        ],
        right_cols={1, 2, 3, 4},
    )

    page_break(doc)
    heading(doc, "4. Monthly revenue and profit", 1)
    body(
        doc,
        f"Sales stay in a narrow band. Best sales month: {best_rev.month} ({money(best_rev.revenue)}). "
        f"Softest: {worst_rev.month} ({money(worst_rev.revenue)}). Best profit month: {best_p.month} "
        f"({money(best_p.profit)}). There is no company-wide festival spike. February looks soft mainly "
        "because it has fewer days.",
    )
    add_chart(doc, fig_monthly(monthly), "monthly_trend.png")
    caption(doc, "Figure 3. Monthly revenue and profit (lakh). The band is tight across 24 months.")

    page_break(doc)
    heading(doc, "5. High sales, low profit margin", 1)
    body(
        doc,
        "These products sit in the top 25% of sales and the bottom 25% of margin. They move a lot of "
        f"money but leave little behind. Company average margin is {pct(margin)}.",
    )
    add_chart(doc, fig_margin(high_low, margin), "thin_margin.png")
    caption(doc, "Figure 4. Margin of the high-sales, low-margin pair vs the company average (dashed).")
    add_table(
        doc,
        ["Product", "Category", "Revenue", "Profit", "Margin"],
        [
            [
                f"{r.product_id}  {r.product_name}",
                r.category,
                money(r.revenue),
                money(r.profit),
                pct(r.margin),
            ]
            for r in high_low.itertuples(index=False)
        ],
        right_cols={2, 3, 4},
    )
    body(
        doc,
        "Cookware Product 89 is the main concern (about 5.01 lakh sales at 9.6% margin). "
        "Mobiles Product 66 is next at 12.1%. Also watch Paper Product 94 (top 10, 15.1%) "
        "and Tables Product 84 (high sales, about 13.4%). Volume is not the same as a healthy mix.",
    )

    page_break(doc)
    heading(doc, "6. What the company should do next", 1)
    heading(doc, "Fix the mix, not only the volume", 2)
    body(
        doc,
        "Review price, discount, and cost on Cookware Product 89 and Mobiles Product 66. "
        "If the discount is too deep, cap it. If cost is high, talk to the supplier or raise the list price. "
        "Do not put extra ad spend on these two until margin improves.",
    )
    heading(doc, "Treat regions as volume, not as profit skill", 2)
    body(
        doc,
        "Do not move budget away from South or East just because North is first. All three keep "
        "about the same profit on each sale. For growth, add coverage in West and Central rather "
        "than assuming those teams underperform.",
    )
    heading(doc, "Do not plan stock on a company-wide season", 2)
    body(
        doc,
        "Total sales barely move from month to month. A big festival stock-up for the whole catalogue "
        "is not supported. If you season stock, do it for a few products only, after a category owner "
        "checks that the same month repeats next year.",
    )
    heading(doc, "Protect the winners", 2)
    body(
        doc,
        "Kids Product 98, the top appliances, and Chairs Product 12 combine high sales with healthy margin. "
        "Keep them in stock and on the homepage. Do not discount them as hard as the weak-margin SKUs.",
    )
    heading(doc, "Clean the product list and the order file", 2)
    body(
        doc,
        "Twelve products sit in the wrong category. Sixty orders have no customer, 35 have no product, "
        "and ten have no real date. Stop loading a sale until those fields are filled. Until sign-up "
        "dates are trustworthy, do not use ‘first purchase after sign-up’ for marketing.",
    )

    heading(doc, "7. Bottom line", 1)
    body(
        doc,
        "The business is steady, not spiky. Profit is even across regions. The real opportunity is mix: "
        "keep pushing the high-margin bestsellers, and stop letting a few high-volume products "
        "quietly dilute company margin.",
    )

    note = doc.add_paragraph()
    n = note.add_run("Source: cleaned star schema. Rebuild with  python scripts/build_insights_report.py")
    n.italic = True
    n.font.size = Pt(9)
    n.font.color.rgb = MUTED

    write_markdown(
        revenue,
        profit,
        margin,
        orders,
        customers,
        top,
        regions,
        monthly,
        high_low,
        best_rev,
        worst_rev,
        best_p,
    )
    DOCS.mkdir(exist_ok=True)
    doc.save(OUT)
    return OUT


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_rows = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return f"{head}\n{sep}\n{body_rows}"


def write_markdown(
    revenue,
    profit,
    margin,
    orders,
    customers,
    top,
    regions,
    monthly,
    high_low,
    best_rev,
    worst_rev,
    best_p,
) -> None:
    top_rows = [
        [
            str(i),
            f"{r.product_id} {r.product_name}",
            r.category,
            money(r.revenue),
            money(r.profit),
            pct(r.margin),
        ]
        for i, r in enumerate(top.itertuples(index=False), start=1)
    ]
    region_rows = [
        [r.region, f"{int(r.orders):,}", money(r.revenue), money(r.profit), pct(r.margin)]
        for r in regions.itertuples(index=False)
    ]
    hl_rows = [
        [
            f"{r.product_id} {r.product_name}",
            r.category,
            money(r.revenue),
            money(r.profit),
            pct(r.margin),
        ]
        for r in high_low.itertuples(index=False)
    ]
    text = f"""# Business Insights Report

**E-commerce leadership pack** · January 2024 – December 2025

This note is for a business review. Numbers come from the cleaned sales model. Returns stay in as negative sales. Orders with a broken date or no product are left out.

## 1. Snapshot

| Metric | Value |
| --- | ---: |
| Revenue | {money(revenue)} |
| Profit | {money(profit)} |
| Profit margin | {pct(margin)} |
| Orders | {orders:,} |
| Customers | {customers:,} |

- Two-year sales {money(revenue)} and profit {money(profit)} — about {pct(margin)} of each rupee of sales is profit.
- The company is steady, not seasonal. The problem is mix: a few high-volume products keep little profit.
- Regions look different in size, but they keep almost the same profit on each sale.

## 2. Top 10 products by revenue

These ten products bring in about one-fifth of product sales. **Kids Product 98** leads on both sales and margin. **Paper Product 94** ranks tenth but keeps much less profit than the rest.

![Top 10 products by revenue](charts/top10_revenue.png)

{md_table(["Rank", "Product", "Category", "Revenue", "Profit", "Margin"], top_rows)}

## 3. Which regions make the most profit?

North makes the most profit, then East and South. West is a little behind because it has four states, not five. Central is only Madhya Pradesh, so its total is smaller. Margin is about 22–23% everywhere. North is not better at profit. It simply sells more.

![Profit by region](charts/profit_by_region.png)

{md_table(["Region", "Orders", "Revenue", "Profit", "Margin"], region_rows)}

## 4. Monthly revenue and profit

Sales stay in a narrow band. Best sales month: **{best_rev.month}** ({money(best_rev.revenue)}). Softest: **{worst_rev.month}** ({money(worst_rev.revenue)}). Best profit month: **{best_p.month}** ({money(best_p.profit)}). There is no company-wide festival spike. February looks soft mainly because it has fewer days.

![Monthly revenue and profit](charts/monthly_trend.png)

## 5. High sales, low profit margin

These products sit in the top 25% of sales and the bottom 25% of margin. Company average margin is {pct(margin)}.

![High sales, thin margin](charts/thin_margin.png)

{md_table(["Product", "Category", "Revenue", "Profit", "Margin"], hl_rows)}

Cookware Product 89 is the main concern (about 5.01 lakh sales at 9.6% margin). Mobiles Product 66 is next at 12.1%. Also watch Paper Product 94 (top 10, 15.1%) and Tables Product 84 (high sales, about 13.4%). Volume is not the same as a healthy mix.

## 6. What the company should do next

### Fix the mix, not only the volume
Review price, discount, and cost on Cookware Product 89 and Mobiles Product 66. If the discount is too deep, cap it. If cost is high, talk to the supplier or raise the list price. Do not put extra ad spend on these two until margin improves.

### Treat regions as volume, not as profit skill
Do not move budget away from South or East just because North is first. All three keep about the same profit on each sale. For growth, add coverage in West and Central rather than assuming those teams underperform.

### Do not plan stock on a company-wide season
Total sales barely move from month to month. A big festival stock-up for the whole catalogue is not supported. If you season stock, do it for a few products only, after a category owner checks that the same month repeats next year.

### Protect the winners
Kids Product 98, the top appliances, and Chairs Product 12 combine high sales with healthy margin. Keep them in stock and on the homepage. Do not discount them as hard as the weak-margin SKUs.

### Clean the product list and the order file
Twelve products sit in the wrong category. Sixty orders have no customer, 35 have no product, and ten have no real date. Stop loading a sale until those fields are filled. Until sign-up dates are trustworthy, do not use “first purchase after sign-up” for marketing.

## 7. Bottom line

The business is steady, not spiky. Profit is even across regions. The real opportunity is mix: keep pushing the high-margin bestsellers, and stop letting a few high-volume products quietly dilute company margin.

---

Source: cleaned star schema. Rebuild with `python scripts/build_insights_report.py`
"""
    OUT_MD.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
