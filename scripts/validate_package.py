"""Run lightweight, reproducible integrity checks on the prepared package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


def row_count(path: Path) -> int:
    with path.open("rb") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    processed = root / "data" / "processed"
    raw = root / "data" / "raw"
    checks: dict[str, object] = {}
    required = [
        processed / "uci_transaction_lines_clean.csv",
        processed / "uci_baskets.csv",
        processed / "uci_weekly_product_demand.csv",
        processed / "uci_copurchase_edges_train_only.csv",
        processed / "m5_schema_profile.json",
        processed / "m5_weekly_product_demand_sample.csv",
        root / "data" / "synthetic" / "inventory_scenarios.csv",
        root / "metadata" / "data_dictionary.csv",
        root / "metadata" / "source_manifest.csv",
    ]
    checks["required_files_present"] = all(path.exists() and path.stat().st_size > 0 for path in required)
    checks["required_file_count"] = len(required)

    transaction_path = processed / "uci_transaction_lines_clean.csv"
    transaction_rows = 0
    invalid_transaction_rows = 0
    for chunk in pd.read_csv(transaction_path, chunksize=100000):
        transaction_rows += len(chunk)
        invalid_transaction_rows += int((chunk["quantity"] <= 0).sum() + (chunk["unit_price_gbp"] <= 0).sum() + chunk["invoice_id"].astype(str).str.startswith("C").sum())
    checks["uci_transaction_rows"] = transaction_rows
    checks["uci_invalid_transaction_rows"] = invalid_transaction_rows

    baskets = pd.read_csv(processed / "uci_baskets.csv")
    checks["uci_basket_rows"] = len(baskets)
    checks["uci_duplicate_basket_ids"] = int(baskets["invoice_id"].duplicated().sum())

    weekly = pd.read_csv(processed / "uci_weekly_product_demand.csv", dtype={"stock_code": "string"})
    checks["uci_weekly_rows"] = len(weekly)
    checks["uci_weekly_negative_units"] = int((weekly["units_sold"] < 0).sum())
    checks["uci_weekly_zero_sales_rows"] = int((weekly["units_sold"] == 0).sum())

    edges = pd.read_csv(processed / "uci_copurchase_edges_train_only.csv")
    checks["copurchase_edge_rows"] = len(edges)
    checks["copurchase_self_edges"] = int((edges["stock_code_a"] == edges["stock_code_b"]).sum())
    checks["copurchase_train_end_values"] = sorted(edges["train_end"].dropna().astype(str).unique().tolist())
    checks["copurchase_negative_counts"] = int((edges["co_purchase_count"] < 0).sum())

    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    checks["synthetic_scenario_rows"] = len(scenarios)
    checks["synthetic_status_values"] = sorted(scenarios["scenario_status"].dropna().unique().tolist())

    manifest_rows = list(csv.DictReader((root / "metadata" / "source_manifest.csv").open(encoding="utf-8", newline="")))
    checks["manifest_rows"] = len(manifest_rows)
    checks["manifest_failures"] = [row["file"] for row in manifest_rows if row["status"].endswith("failed")]
    checks["manifest_files_verified"] = [row["file"] for row in manifest_rows if "verified" in row["status"] or row["status"] == "already_present"]

    m5_sample = processed / "m5_weekly_product_demand_sample.csv"
    checks["m5_sample_rows"] = row_count(m5_sample)
    checks["m5_validation_md5"] = md5_file(raw / "m5" / "sales_train_validation.csv")
    checks["m5_sell_prices_md5"] = md5_file(raw / "m5" / "sell_prices.csv")

    checks["passed"] = bool(
        checks["required_files_present"]
        and checks["uci_invalid_transaction_rows"] == 0
        and checks["uci_duplicate_basket_ids"] == 0
        and checks["uci_weekly_negative_units"] == 0
        and checks["copurchase_self_edges"] == 0
        and checks["copurchase_negative_counts"] == 0
        and not checks["manifest_failures"]
        and checks["m5_sample_rows"] > 0
    )
    report = root / "metadata" / "validation_report.json"
    report.write_text(json.dumps(checks, indent=2, default=str), encoding="utf-8")
    print(json.dumps(checks, indent=2, default=str))
    return 0 if checks["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
