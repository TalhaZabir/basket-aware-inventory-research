"""Prepare the reproducible research tables from the downloaded source files."""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DICTIONARY = [
    ["uci_transaction_lines_clean.csv", "source_row_id", "integer", "source row identifier after concatenating UCI sheets", "observed", "UCI"],
    ["uci_transaction_lines_clean.csv", "invoice_id", "string", "invoice or transaction identifier used to define a completed basket", "observed", "UCI"],
    ["uci_transaction_lines_clean.csv", "invoice_date", "datetime", "transaction timestamp", "observed", "UCI"],
    ["uci_transaction_lines_clean.csv", "stock_code", "string", "product or stock code", "observed", "UCI"],
    ["uci_transaction_lines_clean.csv", "description", "string", "product description as supplied by UCI", "observed", "UCI"],
    ["uci_transaction_lines_clean.csv", "quantity", "integer", "positive units on the retained sale line", "observed", "UCI"],
    ["uci_transaction_lines_clean.csv", "unit_price_gbp", "decimal GBP", "unit price in the source transaction", "observed", "UCI"],
    ["uci_transaction_lines_clean.csv", "line_value_gbp", "decimal GBP", "quantity multiplied by unit price", "derived from observed", "UCI"],
    ["uci_baskets.csv", "invoice_id", "string", "basket key; one row per retained invoice", "observed", "UCI"],
    ["uci_baskets.csv", "line_count", "integer", "retained transaction-line count", "derived from observed", "UCI"],
    ["uci_baskets.csv", "distinct_product_count", "integer", "number of distinct retained products in the basket", "derived from observed", "UCI"],
    ["uci_baskets.csv", "total_units", "integer", "sum of positive quantities in the basket", "derived from observed", "UCI"],
    ["uci_baskets.csv", "basket_value_gbp", "decimal GBP", "sum of retained line values", "derived from observed", "UCI"],
    ["uci_weekly_product_demand.csv", "week_start", "date", "Monday-start week containing the transaction date", "derived from observed", "UCI"],
    ["uci_weekly_product_demand.csv", "stock_code", "string", "product identifier", "observed", "UCI"],
    ["uci_weekly_product_demand.csv", "units_sold", "integer", "weekly positive units; zero for a product-week with no retained sales", "derived from observed", "UCI"],
    ["uci_weekly_product_demand.csv", "transaction_count", "integer", "number of retained invoices containing the product", "derived from observed", "UCI"],
    ["uci_weekly_product_demand.csv", "revenue_gbp", "decimal GBP", "weekly retained transaction value", "derived from observed", "UCI"],
    ["uci_copurchase_edges_train_only.csv", "stock_code_a", "string", "first product in the unordered training-period pair", "observed/derived", "UCI"],
    ["uci_copurchase_edges_train_only.csv", "stock_code_b", "string", "second product in the unordered training-period pair", "observed/derived", "UCI"],
    ["uci_copurchase_edges_train_only.csv", "co_purchase_count", "integer", "number of training baskets containing both products", "derived from observed", "UCI"],
    ["uci_copurchase_edges_train_only.csv", "jaccard", "ratio", "pair basket count divided by union basket count", "derived from observed", "UCI"],
    ["uci_copurchase_edges_train_only.csv", "lift", "ratio", "pair probability divided by product marginal probabilities", "derived from observed", "UCI"],
    ["m5_weekly_product_demand_sample.csv", "id", "string", "M5 item-store series identifier", "observed", "M5"],
    ["m5_weekly_product_demand_sample.csv", "item_id", "string", "M5 product identifier", "observed", "M5"],
    ["m5_weekly_product_demand_sample.csv", "store_id", "string", "M5 store identifier", "observed", "M5"],
    ["m5_weekly_product_demand_sample.csv", "week_start", "date", "Monday-start calendar week", "derived from observed", "M5"],
    ["m5_weekly_product_demand_sample.csv", "units_sold", "integer", "weekly sum of M5 daily unit sales for the sample series", "derived from observed", "M5"],
    ["inventory_scenarios.csv", "scenario_id", "string", "scenario identifier", "synthetic assumption", "Synthetic"],
    ["inventory_scenarios.csv", "lead_time_distribution", "string", "synthetic lead-time distribution family", "synthetic assumption", "Synthetic"],
    ["inventory_scenarios.csv", "holding_cost_per_unit_week", "decimal GBP", "assumed weekly holding cost per unit", "synthetic assumption", "Synthetic"],
    ["inventory_scenarios.csv", "shortage_penalty_per_unit", "decimal GBP", "assumed penalty per unmet unit", "synthetic assumption", "Synthetic"],
    ["inventory_scenarios.csv", "ordering_cost_per_order", "decimal GBP", "assumed fixed ordering cost", "synthetic assumption", "Synthetic"],
]


def normalize_name(name: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def read_uci_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith((".xlsx", ".xls"))]
        if not names:
            raise FileNotFoundError("No Excel file found inside the UCI ZIP archive")
        excel_name = names[0]
        with archive.open(excel_name) as handle:
            workbook = pd.ExcelFile(handle)
            frames = []
            for sheet_name in workbook.sheet_names:
                frame = pd.read_excel(workbook, sheet_name=sheet_name)
                frame.columns = [normalize_name(column) for column in frame.columns]
                frame["source_sheet"] = sheet_name
                frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    aliases = {
        "invoice": "invoice_id",
        "invoice_no": "invoice_id",
        "invoice_number": "invoice_id",
        "stockcode": "stock_code",
        "stock_code": "stock_code",
        "description": "description",
        "quantity": "quantity",
        "invoicedate": "invoice_date",
        "invoice_date": "invoice_date",
        "price": "unit_price_gbp",
        "unit_price": "unit_price_gbp",
        "unit_price_gbp": "unit_price_gbp",
        "customer_id": "customer_id",
        "customerid": "customer_id",
        "country": "country",
    }
    frame = frame.rename(columns={column: aliases.get(column, column) for column in frame.columns})
    required = {"invoice_id", "stock_code", "description", "quantity", "invoice_date", "unit_price_gbp", "customer_id", "country"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"UCI schema missing columns: {sorted(missing)}")
    return frame


def clean_uci(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    frame = raw.copy()
    frame.insert(0, "source_row_id", np.arange(1, len(frame) + 1, dtype=np.int64))
    frame["invoice_id"] = frame["invoice_id"].astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    frame["stock_code"] = frame["stock_code"].astype("string").str.strip().str.upper()
    frame["description"] = frame["description"].astype("string").str.strip()
    frame["customer_id"] = frame["customer_id"].astype("string").str.replace(r"\.0$", "", regex=True).str.strip()
    frame["country"] = frame["country"].astype("string").str.strip()
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="coerce")
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    frame["unit_price_gbp"] = pd.to_numeric(frame["unit_price_gbp"], errors="coerce")
    frame["is_cancellation_or_return"] = frame["invoice_id"].str.upper().str.startswith("C", na=False) | (frame["quantity"] < 0)
    frame["is_merchandise_candidate"] = frame["stock_code"].str.match(r"^\d", na=False)
    frame["line_value_gbp"] = frame["quantity"] * frame["unit_price_gbp"]
    filters = {
        "raw_rows": int(len(frame)),
        "cancellation_or_negative_rows": int(frame["is_cancellation_or_return"].sum()),
        "missing_key_or_date_rows": int(frame[["invoice_id", "stock_code", "invoice_date"]].isna().any(axis=1).sum()),
        "non_merchandise_candidate_rows": int((~frame["is_merchandise_candidate"]).sum()),
        "non_positive_quantity_or_price_rows": int(((frame["quantity"] <= 0) | (frame["unit_price_gbp"] <= 0)).fillna(True).sum()),
    }
    keep = (
        ~frame["is_cancellation_or_return"]
        & frame["is_merchandise_candidate"]
        & frame[["invoice_id", "stock_code", "invoice_date", "description"]].notna().all(axis=1)
        & (frame["quantity"] > 0)
        & (frame["unit_price_gbp"] > 0)
    )
    clean = frame.loc[keep, ["source_row_id", "invoice_id", "invoice_date", "stock_code", "description", "quantity", "unit_price_gbp", "line_value_gbp", "customer_id", "country", "source_sheet"]].copy()
    clean["quantity"] = clean["quantity"].astype("int64")
    clean["invoice_date"] = clean["invoice_date"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    filters["retained_rows"] = int(len(clean))
    filters["retained_invoices"] = int(clean["invoice_id"].nunique())
    filters["retained_products"] = int(clean["stock_code"].nunique())
    filters["date_min"] = str(clean["invoice_date"].min()) if len(clean) else None
    filters["date_max"] = str(clean["invoice_date"].max()) if len(clean) else None
    return clean, filters


def write_uci_outputs(clean: pd.DataFrame, output_dir: Path, train_end: str, min_product_baskets: int, min_pair_count: int) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean = clean.copy()
    clean["invoice_date_dt"] = pd.to_datetime(clean["invoice_date"])
    clean.drop(columns=["invoice_date_dt"]).to_csv(output_dir / "uci_transaction_lines_clean.csv", index=False)

    baskets = clean.groupby("invoice_id", as_index=False).agg(
        invoice_date=("invoice_date_dt", "min"),
        customer_id=("customer_id", "first"),
        country=("country", "first"),
        line_count=("stock_code", "size"),
        distinct_product_count=("stock_code", "nunique"),
        total_units=("quantity", "sum"),
        basket_value_gbp=("line_value_gbp", "sum"),
    )
    baskets["invoice_date"] = baskets["invoice_date"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    baskets.to_csv(output_dir / "uci_baskets.csv", index=False)

    clean["week_start"] = clean["invoice_date_dt"].dt.normalize() - pd.to_timedelta(clean["invoice_date_dt"].dt.weekday, unit="D")
    observed = clean.groupby(["stock_code", "week_start"], as_index=False).agg(
        units_sold=("quantity", "sum"), transaction_count=("invoice_id", "nunique"), revenue_gbp=("line_value_gbp", "sum"),
        average_unit_price_gbp=("unit_price_gbp", "mean"),
    )
    product_meta = clean.groupby("stock_code", as_index=False).agg(description=("description", "first"))
    weeks = pd.date_range(clean["week_start"].min(), clean["week_start"].max(), freq="7D")
    universe = product_meta.assign(_key=1).merge(pd.DataFrame({"week_start": weeks, "_key": 1}), on="_key").drop(columns="_key")
    weekly = universe.merge(observed, on=["stock_code", "week_start"], how="left")
    for column in ["units_sold", "transaction_count", "revenue_gbp"]:
        weekly[column] = weekly[column].fillna(0)
    weekly["is_observed_sales_week"] = weekly["transaction_count"].gt(0)
    weekly["week_start"] = weekly["week_start"].dt.strftime("%Y-%m-%d")
    weekly.to_csv(output_dir / "uci_weekly_product_demand.csv", index=False)

    train = clean.loc[clean["invoice_date_dt"] <= pd.Timestamp(train_end)].copy()
    invoice_products = train.groupby("invoice_id")["stock_code"].apply(lambda values: sorted(set(values)))
    support = Counter(product for products in invoice_products for product in products)
    eligible = {product for product, count in support.items() if count >= min_product_baskets}
    pair_counts: Counter[tuple[str, str]] = Counter()
    eligible_basket_count = 0
    for products in invoice_products:
        products = [product for product in products if product in eligible]
        if products:
            eligible_basket_count += 1
            pair_counts.update(itertools.combinations(products, 2))
    names = train.groupby("stock_code")["description"].first().to_dict()
    rows = []
    for (a, b), count in pair_counts.items():
        if count < min_pair_count:
            continue
        sa, sb = support[a], support[b]
        union = sa + sb - count
        pair_probability = count / max(eligible_basket_count, 1)
        marginal_a = sa / max(eligible_basket_count, 1)
        marginal_b = sb / max(eligible_basket_count, 1)
        rows.append({
            "stock_code_a": a, "description_a": names.get(a, ""), "stock_code_b": b, "description_b": names.get(b, ""),
            "training_basket_support_a": sa, "training_basket_support_b": sb, "co_purchase_count": count,
            "co_purchase_rate": pair_probability, "p_b_given_a": count / sa, "p_a_given_b": count / sb,
            "jaccard": count / union if union else np.nan, "lift": pair_probability / (marginal_a * marginal_b) if marginal_a and marginal_b else np.nan,
            "train_end": train_end,
        })
    edges = pd.DataFrame(rows).sort_values(["co_purchase_count", "lift"], ascending=[False, False]) if rows else pd.DataFrame(columns=["stock_code_a", "stock_code_b", "co_purchase_count"])
    edges.to_csv(output_dir / "uci_copurchase_edges_train_only.csv", index=False)
    return {"weekly_rows": int(len(weekly)), "training_invoices": int(len(invoice_products)), "eligible_training_products": int(len(eligible)), "copurchase_edges": int(len(edges)), "train_end": train_end}


def profile_m5(m5_dir: Path, output_dir: Path, sample_series: int = 200) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = ["calendar.csv", "sales_train_validation.csv", "sales_train_evaluation.csv", "sell_prices.csv", "sample_submission.csv"]
    profiles = {}
    for filename in files:
        path = m5_dir / filename
        if not path.exists():
            profiles[filename] = {"status": "missing"}
            continue
        sample = pd.read_csv(path, nrows=5)
        sample_columns = list(sample.columns) if len(sample.columns) <= 20 else list(sample.columns[:10]) + list(sample.columns[-3:])
        with path.open("rb") as handle:
            row_count = max(sum(1 for _ in handle) - 1, 0)
        profiles[filename] = {"status": "present", "bytes": path.stat().st_size, "rows": int(row_count), "column_count": len(sample.columns), "columns": list(sample.columns), "sample_columns": sample_columns, "sample": sample[sample_columns].astype(object).where(pd.notna(sample[sample_columns]), None).to_dict(orient="records")}

    calendar_path = m5_dir / "calendar.csv"
    sales_path = m5_dir / "sales_train_validation.csv"
    if calendar_path.exists() and sales_path.exists():
        calendar = pd.read_csv(calendar_path, usecols=["d", "date"])
        calendar["date"] = pd.to_datetime(calendar["date"])
        calendar["week_start"] = calendar["date"].dt.normalize() - pd.to_timedelta(calendar["date"].dt.weekday, unit="D")
        sales = pd.read_csv(sales_path, nrows=sample_series)
        day_columns = [column for column in sales.columns if column.startswith("d_")]
        week_groups = calendar.loc[calendar["d"].isin(day_columns)].groupby("week_start")["d"].apply(list)
        rows = []
        id_columns = [column for column in ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"] if column in sales.columns]
        for _, record in sales.iterrows():
            for week_start, days in week_groups.items():
                rows.append({**{column: record[column] for column in id_columns}, "week_start": week_start.strftime("%Y-%m-%d"), "units_sold": int(record[days].sum())})
        pd.DataFrame(rows).to_csv(output_dir / "m5_weekly_product_demand_sample.csv", index=False)
    else:
        pd.DataFrame(columns=["id", "item_id", "store_id", "week_start", "units_sold"]).to_csv(output_dir / "m5_weekly_product_demand_sample.csv", index=False)
    with (output_dir / "m5_schema_profile.json").open("w", encoding="utf-8") as handle:
        json.dump(profiles, handle, indent=2, default=str)
    return {"files": profiles, "sample_series": sample_series}


def write_dictionary(root: Path) -> None:
    path = root / "metadata" / "data_dictionary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(DATA_DICTIONARY, columns=["file", "field", "type_or_unit", "definition", "status", "source"]).to_csv(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--all", action="store_true", help="Prepare UCI and profile M5")
    parser.add_argument("--uci-zip", default=None)
    parser.add_argument("--m5-dir", default=None)
    parser.add_argument("--train-end", default="2011-06-30")
    parser.add_argument("--min-product-baskets", type=int, default=20)
    parser.add_argument("--min-pair-count", type=int, default=5)
    parser.add_argument("--m5-sample-series", type=int, default=200)
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    processed = root / "data" / "processed"
    metadata = root / "metadata"
    write_dictionary(root)
    summary: dict[str, object] = {}
    uci_zip = Path(args.uci_zip).resolve() if args.uci_zip else root / "data" / "raw" / "uci_online_retail_ii.zip"
    if args.all or uci_zip.exists():
        if not uci_zip.exists():
            raise FileNotFoundError(f"UCI ZIP not found: {uci_zip}")
        raw = read_uci_zip(uci_zip)
        clean, cleaning_summary = clean_uci(raw)
        summary["uci_cleaning"] = cleaning_summary
        summary["uci_outputs"] = write_uci_outputs(clean, processed, args.train_end, args.min_product_baskets, args.min_pair_count)
    m5_dir = Path(args.m5_dir).resolve() if args.m5_dir else root / "data" / "raw" / "m5"
    if args.all or m5_dir.exists():
        summary["m5"] = profile_m5(m5_dir, processed, args.m5_sample_series)
    metadata.mkdir(parents=True, exist_ok=True)
    with (metadata / "cleaning_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, default=str)
    print(json.dumps({"root": str(root), "summary": summary}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
