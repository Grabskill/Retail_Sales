# E-commerce Sales Analytics Pipeline

Turn messy operational CSVs into a **star schema** and an interactive **Streamlit** dashboard that a commercial team can filter by year, region, and category. Business Insights are provided in docs/Business_Insights_Report.pdf

---

## 1. Project overview and value proposition


This project takes four raw files (`orders`, `customers`, `products`, `regions`) covering **Jan 2024–Dec 2025** and produces:

| Layer          | What you get                                                      |
| :------------- | :---------------------------------------------------------------- |
| Profiling      | Row counts, keys, missingness, categorical drift, FK checks       |
| Cleaning       | Reproducible Pandas pipeline in `scripts/`                        |
| Model          | Star schema under `cleaned_files/`                                |
| Audit metrics  | Independent KPI CSVs in `reports/`,final report in docs           |
| Interface      | Streamlit app in `web/app.py`                                     |

**What this solves**

- Duplicate load rows no longer double-count revenue.
- Invalid dates and missing keys are **flagged**, not silently filled.
- Category spelling variants (`electronics`, `OFFICE SUPPLIES`, trailing spaces) do not fragment charts.
- Returns (negative quantity) stay in the fact table with `is_return`, so net sales remain honest.

**Technical highlights**

| Area         | Choice                                      |
| :----------- | :------------------------------------------ |
| Language     | Python 3                                    |
| Wrangling    | Pandas                                      |
| Model        | Star schema (`fact_sales` + four dimensions) |
| Grain        | One fact row per order line (`order_id`)    |
| App          | Streamlit + Plotly                          |
| Environment  | `.venv`                                     |

---

## 2. Data architecture and the star schema

There is **no `dim_order` table**. Each cleaned order is one product line, so `order_id` is a **one-to-one** degenerate key on the fact row. Time is `dim_date`. Grain of `fact_sales` = **one line-item / one `order_id`** (25,000 rows after de-duplication). Measures sit on the fact; attributes sit on dimensions.

```
                         dim_date
                         731 rows
                         date_key (PK)
                         date, day, month,
                         month_name, quarter, year
                              ▲
                              │ order_date = date
                              │
dim_customer                  │                    dim_product
2,000 rows                    │                    100 rows
customer_id (PK) ──────►  FACT_SALES  ◄──────────  product_id (PK)
name, gender, age,        25,000 rows              name, category,
segment, signup_date      order_id (degenerate PK)  sub_category,
                              │                    cost, selling_price
                              │                    + category audit cols
                              │ region_id
                              ▼
                         dim_region
                         20 rows
                         region_id (PK)
                         state, city, region
```

## 3. Pipeline engineering and cleaning interventions


python scripts/profile_data.py
python scripts/clean_data.py
python scripts/evaluate_metrics.py

### What the pipeline actually does

| Intervention       | Rule used here                                                                 |
| :----------------- | :----------------------------------------------------------------------------- |
| Profiling          | Full pass on four raw CSVs before any transform                                |
| Deduplication      | Drop 10 extra customer rows and 50 extra order rows; keep first                |
| Missing keys       | Not imputed. Flagged on the fact table                                         |
| Datetime           | Valid timestamps → `YYYY-MM-DD`; `not_a_date` → null + `invalid_order_date`    |
| Text               | Product `category` trimmed and case-folded to a closed list                    |
| Category sanity    | Majority `sub_category → category` map; mismatches flagged, not overwritten    |
| Returns            | Negative quantity kept; `is_return = True`                                     |
| Calendar           | `dim_date` from valid fact dates only (2024–2025, 731 days)                    |

Missing customer/product IDs are **not** filled with statistical defaults. 

### Representative pipeline snippets

Deduplicate customers to one row per business key:

```python
customers.drop_duplicates(subset=["customer_id"], keep="first")
```

Standardize category labels, then flag — do not silently rewrite — inconsistent sub-categories:

```python
products["category"] = products["category"].map(standardize_category)
products["suggested_category"] = products["sub_category"].map(majority_category)
products["category_subcategory_mismatch"] = (
    products["category"] != products["suggested_category"]
)
```

Isolate bad dates and returns without dropping commercial history:

```python
parsed = pd.to_datetime(orders["order_date"], errors="coerce")
orders["invalid_order_date"] = parsed.isna()
orders["is_return"] = orders["quantity"] < 0
```

### Raw → cleaned volumes

| Extract              | Raw rows | Cleaned table        | Cleaned rows |
| :------------------- | -------: | :------------------- | -----------: |
| `orders_raw.csv`     |   25,050 | `fact_sales.csv`     |       25,000 |
| `customers_raw.csv`  |    2,010 | `dim_customer.csv`   |        2,000 |
| `products_raw.csv`   |      100 | `dim_product.csv`    |          100 |
| `regions_raw.csv`    |       20 | `dim_region.csv`     |           20 |

---

## 4. Business insights and Streamlit interface


Headline results on valid, product-attributed orders:

| KPI                  |        Value |
| :------------------- | -----------: |
| Revenue              |   29,449,585 |
| Profit               |    6,748,690 |
| Margin               |        22.9% |
| Orders               |       24,955 |
| Distinct customers   |        2,000 |
| Return lines         |           15 |

### questions the model is built to answer

1.	What are the top 10 products by revenue?
2.	Which regions generate the highest profit?
3.	Show monthly revenue and profit.
4.	Which products have high revenue but low profit margin?


### Streamlit frontend (`web/app.py`)

The app reads the star schema from `cleaned_files/`, caches the joined frame, and applies three sidebar-style selectors:

| Control   | Values                                                       |
| :-------- | :----------------------------------------------------------- |
| Year      | All years, 2024, 2025                                        |
| Region    | All regions, Central, East, North, South, West               |
| Category  | All categories plus the five standardized product categories |

Every control recomputes:

1. KPI row — revenue, profit, orders, customers  
2. Monthly revenue and profit line (Plotly)  
3. Revenue by category  
4. Profit by region  
5. Top 10 products with margin

Invalid dates and missing product IDs are filtered out in `load_data()` so category charts cannot show an “Unknown” bucket by accident.

---

## 5. Step-by-step run instructions

Tested on Windows 10 with PowerShell. Python 3.10+ recommended.

python -m venv .venv -> .\.venv\Scripts\Activate.ps1 -> python -m pip install -r requirements.txt -> python scripts/[file_name].py -> python -m streamlit run web/app.py


---

## Repository layout

```text
cursorai_proj1/
├── customers_raw.csv          # raw extract
├── orders_raw.csv
├── products_raw.csv
├── regions_raw.csv
├── cleaned_files/             # star schema (regenerated by clean_data.py)
│   ├── fact_sales.csv
│   ├── dim_customer.csv
│   ├── dim_product.csv
│   ├── dim_region.csv
│   └── dim_date.csv
├── scripts/
│   ├── profile_data.py
│   ├── clean_data.py
│   └── evaluate_metrics.py
├── web/
│   ├── app.py                 # Streamlit
│   ├── dashboard.html
│   ├── dashboard_data.js
│   └── requirements.txt
├── requirements.txt
└── README.md
```

---


